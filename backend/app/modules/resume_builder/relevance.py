"""Which of the learner's items best fit THIS job? Transparent scoring, no black box.

Score (0-100) per item = weighted blend of
  * TF-IDF cosine similarity between the item's text and the job text,
  * coverage of the job's keywords by the item,
  * recency,
  * quantified impact (numbers present), weighted higher for sales/ops/product style roles.
Every score carries human-readable reasons shown in the UI.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Any, Literal

from app.modules import textsim
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.modules.careerverse import gemini_service as g
from app.modules.learning.ai import Lenient
from app.modules.resume_builder import pool as P

from pydantic import Field

logger = get_logger(__name__)
ROLE_TYPES = ("tech", "data", "finance", "consulting", "product", "sales", "marketing", "operations", "general")
IMPACT_HEAVY = {"sales", "marketing", "operations", "product"}
STOP = set("a an and are as at be by for from has have in is it its of on or that the to with will you your we our this these their they who whom which what when where while about into over under more most other such than then them there those can may must should would could not no nor per via etc using use used including include within across able ability experience years year work working team teams strong good great plus preferred required responsibilities requirements role job candidate company looking join".split())

# caps mirror the template's density (it carries 2 experience, 3 projects, 2 leadership, 1 certification)
CAPS = {"experience": 3, "project": 3, "leadership": 2, "certification": 2, "achievement": 9}


class JDAnalysis(Lenient):
    role_type: Literal["tech", "data", "finance", "consulting", "product", "sales", "marketing", "operations", "general"] = "general"
    seniority: str = ""
    keywords: list[str] = Field(default_factory=list)
    emphasis: list[str] = Field(default_factory=list)
    inferred: bool = False


_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("sales", ("sales", "business development", "account executive", "account manager", "bd manager", "inside sales", "revenue")),
    ("marketing", ("marketing", "brand", "seo", "content", "growth", "social media", "campaign")),
    ("product", ("product manager", "product owner", "apm", "product analyst", "product management")),
    ("consulting", ("consultant", "consulting", "strategy")),
    ("finance", ("investment", "banking", "equity", "quant", "treasury", "financial analyst", "valuation", "portfolio", "credit", "risk analyst", "finance", "private equity", "venture")),
    ("data", ("data scientist", "data analyst", "data engineer", "machine learning", "ml engineer", "analytics", "ai engineer", "business intelligence", "bi analyst")),
    ("tech", ("engineer", "developer", "software", "backend", "frontend", "full stack", "devops", "sde", "programmer", "security", "cloud", "sre")),
    ("operations", ("operations", "supply chain", "logistics", "project manager", "program manager", "procurement")),
]


def tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9+#.]{2,}", (text or "").lower()) if t not in STOP]


def local_analysis(title: str, jd: str) -> dict[str, Any]:
    """Fallback when Gemini is unavailable: rule-based role type and frequency-based keywords."""
    blob = f"{title} {jd[:600]}".lower()
    role = next((r for r, keys in _RULES if any(k in blob for k in keys)), "general")
    freq: dict[str, int] = {}
    for t in tokens(f"{title} {title} {jd}"):
        if len(t) > 2 and not t.isdigit():
            freq[t] = freq.get(t, 0) + 1
    kws = [k for k, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:25]]
    return {"role_type": role, "seniority": "", "keywords": kws, "emphasis": [], "inferred": not jd.strip(), "source": "rule_based"}


def analyse_jd(db: Session, title: str, company: str | None, jd: str | None) -> dict[str, Any]:
    jd = (jd or "").strip()
    base = local_analysis(title, jd)
    if not g.is_enabled():
        return base
    prompt = (
        "Analyse this job for a resume-tailoring tool. Return JSON {\"role_type\": one of "
        f"{list(ROLE_TYPES)}, \"seniority\": str, \"keywords\": [up to 25 specific skills, tools, methods and domain terms the employer wants], "
        "\"emphasis\": [3-5 short phrases describing what the employer values most], \"inferred\": bool}. "
        + ("Take keywords ONLY from the posting. " if jd else "No posting was supplied, so infer the typical requirements for this title and set inferred=true. ")
        + f"\nTITLE: {title}\nCOMPANY: {company or 'n/a'}\nPOSTING:\n{jd[:6000] or '(none)'}"
    )
    out = g.cached_json(db, "resume_jd", (title.lower(), (company or "").lower(), jd[:6000]), prompt, schema=JDAnalysis, temperature=0.2, max_tokens=900)
    if not out:
        return base
    kws = list(dict.fromkeys([k.strip() for k in out.get("keywords", []) if k.strip()] + base["keywords"][:6]))[:30]
    return {**out, "keywords": kws, "source": "gemini"}


def _match_keywords(item_text: str, keywords: list[str]) -> list[str]:
    low = item_text.lower()
    toks = set(tokens(item_text))
    hit = []
    for k in keywords:
        kl = k.lower()
        kt = tokens(k)
        if kl in low or (kt and all(t in toks for t in kt)):
            hit.append(k)
    return hit


def score_items(items: list[P.Item], analysis: dict[str, Any], title: str, jd: str, today: dt.date | None = None) -> dict[str, dict[str, Any]]:
    today = today or dt.date.today()
    keywords: list[str] = analysis["keywords"]
    role = analysis["role_type"]
    job_text = " ".join([title, jd or "", " ".join(keywords)])
    cos: list[float] = [0.0] * len(items)
    if items and tokens(job_text):
        cos = textsim.similarities([it.text for it in items], job_text, token_pattern=textsim.SKILL_TOKEN)
    w_cos, w_kw, w_rec, w_imp = (0.40, 0.30, 0.10, 0.20) if role in IMPACT_HEAVY else (0.50, 0.30, 0.10, 0.10)
    out: dict[str, dict[str, Any]] = {}
    for it, c in zip(items, cos):
        matched = _match_keywords(it.text, keywords)
        kw = min(1.0, len(matched) / 6) if keywords else 0.0
        c_cal = min(1.0, c / 0.30)
        end = it.end or it.start
        if it.current:
            rec = 1.0
        elif end:
            years = max(0.0, (today - end).days / 365)
            rec = max(0.2, 1.0 - years / 5)
        else:
            rec = 0.5
        nums = P.numbers_in(it.text)
        imp = min(1.0, len(nums) / 3)
        score = 100 * (w_cos * c_cal + w_kw * kw + w_rec * rec + w_imp * imp)
        reasons = []
        if matched:
            reasons.append("Matches: " + ", ".join(matched[:5]))
        if c_cal >= 0.5:
            reasons.append("Wording closely mirrors the role")
        if nums:
            reasons.append("Contains measurable results")
        elif role in IMPACT_HEAVY:
            reasons.append("No numbers yet (this role favours quantified results)")
        if it.current:
            reasons.append("Current")
        out[it.ref] = {"score": round(score, 1), "matched": matched, "reasons": reasons or ["General background"]}
    return out


def choose(items: list[P.Item], scores: dict[str, dict[str, Any]]) -> dict[str, list[P.Item]]:
    """Top-scoring items per section within the template's density caps."""
    chosen: dict[str, list[P.Item]] = {}
    for kind, cap in CAPS.items():
        pool = sorted([i for i in items if i.kind == kind], key=lambda i: -scores[i.ref]["score"])
        chosen[kind] = pool[:cap]
    return chosen


def rank_skills(skills: list[dict[str, str]], keywords: list[str]) -> list[dict[str, Any]]:
    kw = {k.lower() for k in keywords}
    kwt = set(t for k in keywords for t in tokens(k))
    ranked = []
    for idx, s in enumerate(skills):
        n = s["name"].lower()
        m = 1.0 if n in kw else (0.5 if set(tokens(s["name"])) & kwt else 0.0)
        ranked.append({**s, "match": m, "order": idx})
    return sorted(ranked, key=lambda r: (-r["match"], r["order"]))


_TIER = [
    ("First Place", re.compile(r"\b(first|1st|winner|champion|gold)\b", re.I)),
    ("Second / Third Place", re.compile(r"\b(second|2nd|third|3rd|runner[- ]?up|silver|bronze)\b", re.I)),
    ("Finalist", re.compile(r"\b(finalist|top\s?\d+|shortlist\w*|semi[- ]?final\w*)\b", re.I)),
]


def group_achievements(items: list[P.Item]) -> list[dict[str, str]]:
    """Group into 'First Place: a; b' lines like the template."""
    buckets: dict[str, list[str]] = {"First Place": [], "Second / Third Place": [], "Finalist": [], "Recognition": []}
    for it in items:
        label = "Recognition"
        for name, rx in _TIER:
            if rx.search(it.title):
                label = name
                break
        txt = re.sub(r"^\s*(first|second|third|1st|2nd|3rd)\s*(place|prize|position)?\s*[:\-–—,]*\s*|^\s*(winner|finalist|champion)\s*[:\-–—,]*\s*", "", it.title, flags=re.I).strip() or it.title
        buckets[label].append(txt)
    return [{"label": k, "text": "; ".join(v)} for k, v in buckets.items() if v]
