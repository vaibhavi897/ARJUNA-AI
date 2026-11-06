"""Rewrite each chosen item's bullets for the target role, using ONLY the learner's own facts.

Guardrails enforced in code, not just in the prompt:
  * every number in a rewritten bullet must already appear in that item's source text
    (so "increased sales 40%" can never appear unless the profile says 40);
  * bullets must fit two lines at the template's width, else they are shortened;
  * if Gemini is unavailable or a bullet fails validation, the learner's original
    wording is used and the entry is flagged. Nothing is silently invented.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import Field
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.modules.careerverse import gemini_service as g
from app.modules.learning.ai import Lenient
from app.modules.resume_builder import layout, pool as P
from app.modules.resume_builder.relevance import IMPACT_HEAVY

logger = get_logger(__name__)

STYLE = {
    "sales": "Lead every bullet with the business outcome and put the NUMBERS first (revenue, pipeline, conversion, growth %, customers, deal size, quota). Persuasive, results-driven verbs.",
    "marketing": "Lead with measurable outcomes (reach, engagement, leads, conversion, growth %). Campaign, channel and audience language.",
    "tech": "Be technically precise: name the stack, architecture, scale, performance, testing and deployment. Dense, specific engineering vocabulary; avoid vague business filler.",
    "data": "Name the data, methods, models, metrics and pipelines. Quantify dataset size, accuracy or impact when the facts give it.",
    "finance": "Use analytical finance vocabulary: valuation, modelling, instruments, risk, portfolio, research. Name the frameworks and coverage size.",
    "consulting": "Structure as problem, approach, impact. Stakeholders, frameworks, synthesis and recommendations.",
    "product": "Frame around the user problem, decisions, shipped outcomes and metrics, with cross-functional collaboration.",
    "operations": "Emphasise process, efficiency, volume, turnaround, SLAs and coordination.",
    "general": "Clear action plus result. Use numbers only where the facts provide them.",
}


class Rewritten(Lenient):
    id: str
    bullets: list[str] = Field(default_factory=list)


class TailorOut(Lenient):
    items: list[Rewritten] = Field(min_length=1)


def _bold_balanced(s: str) -> str:
    s = re.sub(r"\*{3,}", "**", s)
    if s.count("**") % 2:
        s = s.replace("**", "", 1) if s.rindex("**") == s.index("**") else s[: s.rindex("**")] + s[s.rindex("**") + 2:]
    s = s.replace("*", "") if s.count("*") % 2 else s
    return _limit_bold(s.strip())


def _limit_bold(s: str, keep: int = 2) -> str:
    """Bold at most ``keep`` spans so the page keeps the template's restrained look."""
    n = 0

    def sub(m: re.Match) -> str:
        nonlocal n
        n += 1
        return m.group(0) if n <= keep else m.group(1)

    return re.sub(r"\*\*(.+?)\*\*", sub, s)


def _digits(s: str) -> set[str]:
    return P.numbers_in(re.sub(r"\*\*", "", s))


_CAP_OK = {"I"}


def _unsupported_terms(b: str, facts: str, extra: str = "") -> list[str]:
    """Capitalised words (tools, employers, titles) in a bullet that the source facts never mention."""
    plain = re.sub(r"\*", "", b)
    low = (facts + " " + extra).lower()
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.\-]*", plain)
    bad = []
    for i, w in enumerate(words):
        if i == 0 or w in _CAP_OK or not (w[0].isupper() or any(c.isupper() for c in w[1:])):
            continue
        if w.lower().rstrip(".") not in low:
            bad.append(w)
    return bad


def _fits_two_lines(b: str) -> bool:
    return layout.line_count(b, layout.TEXT_W, layout.BODY, layout.BULLET_INDENT) <= 2


def _shorten(b: str) -> str | None:
    """Trim trailing clauses until the bullet fits two lines; None if that destroys it."""
    cur = b
    for _ in range(6):
        if _fits_two_lines(cur):
            return _bold_balanced(cur)
        cut = max(cur.rfind(", "), cur.rfind("; "))
        if cut < 70:
            break
        cur = cur[:cut].rstrip(" ,;") + "."
    return _bold_balanced(cur) if _fits_two_lines(cur) and len(cur) >= 50 else None


def _original_bullets(item: P.Item, n: int = 2) -> list[str]:
    out: list[str] = []
    for s in item.sentences:
        s = s.strip().rstrip(".") + "."
        short = s if _fits_two_lines(s) else _shorten(s)
        if short:
            out.append(short)
        if len(out) >= n:
            break
    return out


def _validate(item: P.Item, bullets: list[str], role: str) -> tuple[list[str], list[str]]:
    """Return (clean bullets, flags)."""
    flags: list[str] = []
    allowed = _digits(item.text)
    clean: list[str] = []
    for b in bullets:
        b = _bold_balanced(b)
        if len(b) < 25:
            continue
        extra = _digits(b) - allowed
        if extra:
            flags.append(f"Removed an unsupported number ({', '.join(sorted(extra))}) that is not in your profile")
            continue
        terms = _unsupported_terms(b, item.text)
        if terms:
            flags.append(f"Removed a bullet that mentioned something not in your profile ({', '.join(t.rstrip('.') for t in terms[:3])})")
            continue
        if not _fits_two_lines(b):
            b = _shorten(b) or ""
            if not b:
                flags.append("A bullet was too long to fit and was dropped")
                continue
        clean.append(b)
    return clean[:2], flags


def tailor(db: Session, items: list[P.Item], analysis: dict[str, Any], title: str, company: str | None) -> dict[str, dict[str, Any]]:
    """Return {ref: {"bullets": [...], "flags": [...], "source": "gemini" | "original"}} for experience/project/leadership items."""
    role = analysis["role_type"]
    result: dict[str, dict[str, Any]] = {}
    todo = [i for i in items if i.kind in ("experience", "project", "leadership")]
    ai_out: dict[str, list[str]] = {}
    if todo and g.is_enabled():
        for k in range(0, len(todo), 6):
            chunk = todo[k:k + 6]
            facts = [{"id": it.ref, "kind": it.kind, "title": it.title, "organisation": it.org, "tense": "present (ongoing role)" if it.current else "past (finished)", "current": it.current, "technologies_and_skills": it.tags[:15],
                      "facts": it.text[:1800], "numbers_in_facts": sorted(P.numbers_in(it.text))} for it in chunk]
            ask = (
                f"Rewrite resume bullets for a candidate applying to: {title}" + (f" at {company}" if company else "") + f". Role type: {role}.\n"
                f"STYLE: {STYLE.get(role, STYLE['general'])}\n"
                f"The employer values: {analysis.get('emphasis') or 'n/a'}; keywords: {analysis.get('keywords', [])[:20]}.\n"
                "For EACH item write exactly 2 bullets (1 if the facts are thin) using ONLY the facts provided. Strict rules: "
                "(1) NEVER add a number, percentage, tool, company, job title, purpose, environment or outcome that is not in the facts (do not say 'for caching', 'in production', 'load testing', 'as a <title>' unless the facts say so); (2) keep every number exactly as written and keep each action's real meaning (if the facts say 'called 200 leads' never say 'generated 200 leads'); "
                "(3) naturally weave in the employer's keywords ONLY where the facts genuinely support them; "
                "(4) each bullet is one sentence of at most 200 characters starting with a strong verb (use the item's \"tense\" field: PAST tense verbs like Built/Closed for finished items, present only if ongoing); "
                "(5) wrap the 1-2 most important metrics or phrases in **double asterisks** for bold; (6) no first person, no filler.\n"
                "Return JSON {\"items\": [{\"id\": str, \"bullets\": [str, str]}]} with the same ids.\n"
                f"ITEMS: {facts}"
            )
            try:
                data = g.generate_json(ask, schema=TailorOut, temperature=0.4, max_tokens=3500, retries=2)
                for r in data["items"]:
                    ai_out[r["id"]] = r["bullets"]
            except g.GeminiUnavailable as exc:
                logger.warning("resume tailoring unavailable: %s", exc)
    for it in todo:
        bullets, flags = _validate(it, ai_out.get(it.ref, []), role)
        source = "gemini"
        if not bullets:
            bullets, source = _original_bullets(it), "original"
            flags.append("Kept your original wording" + ("" if g.is_enabled() else " (AI tailoring unavailable)"))
        if not bullets:
            bullets = [it.title] if it.title else []
            flags.append("Add a description to this item in your profile for stronger bullets")
        if role in IMPACT_HEAVY and bullets and not any(re.search(r"\d", b) for b in bullets):
            flags.append("No measurable result found. Add a number in your profile or edit the bullet")
        result[it.ref] = {"bullets": bullets, "flags": list(dict.fromkeys(flags)), "source": source}
    return result
