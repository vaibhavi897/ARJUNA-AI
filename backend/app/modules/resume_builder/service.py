"""Generate, fit, swap and edit tailored resumes."""

from __future__ import annotations

import copy
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.models import ResumeVersion, User
from app.modules.resume_builder import layout, pool as P, relevance as R, tailor as T

logger = get_logger(__name__)
SECTION_TITLES = {"education": "Education", "experience": "Experience", "projects": "Projects", "leadership": "Leadership", "certifications": "Certifications", "achievements": "Achievements", "skills": "Skills"}
EXTRA = 1          # tailor one more candidate per section than fits, then trim to the page
SKILL_CAPS = {"Technical": 18, "Concepts": 12, "Soft Skills": 7}
ORDER = {"tech": ["Technical", "Concepts", "Soft Skills"], "data": ["Technical", "Concepts", "Soft Skills"],
         "finance": ["Concepts", "Technical", "Soft Skills"], "consulting": ["Concepts", "Soft Skills", "Technical"],
         "product": ["Concepts", "Technical", "Soft Skills"], "sales": ["Concepts", "Soft Skills", "Technical"],
         "marketing": ["Concepts", "Soft Skills", "Technical"], "operations": ["Concepts", "Soft Skills", "Technical"], "general": ["Technical", "Concepts", "Soft Skills"]}


# ---------------------------------------------------------------- content construction
def _recency_key(it: P.Item) -> tuple:
    return (1 if it.current else 0, (it.end or it.start).toordinal() if (it.end or it.start) else 0)


def _entry(it: P.Item, bullets: list[str]) -> dict[str, Any]:
    right = P.date_range(it.start, it.end, it.current)
    e: dict[str, Any] = {"right": right, "bullets": bullets, "source": {"ref": it.ref}}
    if it.kind == "experience":
        e["title"] = f"**{it.org}** - {it.title}" if it.org else f"**{it.title}**"
    elif it.kind == "leadership":
        e["title"] = f"**{it.title}** — *{it.org}*" if it.org else f"**{it.title}**"
    else:
        e["title"] = f"**{it.title}**"
        if it.org:
            e["subtitle"] = it.org
    return e


def build_content(pl: P.Pool, chosen: dict[str, list[P.Item]], tailored: dict[str, dict[str, Any]], analysis: dict[str, Any]) -> dict[str, Any]:
    sections: list[dict[str, Any]] = []
    if pl.education:
        sections.append({"key": "education", "title": SECTION_TITLES["education"], "type": "entries", "entries": [
            {"title": f"**{e['institution']}**", "right": e["right"], "subtitle": e["degree"], "subright": f"**{e['score']}**" if e["score"] else "", "bullets": [], "source": {"ref": f"education:{e['id']}"}} for e in pl.education[:2]]})
    for kind, key in (("experience", "experience"), ("project", "projects"), ("leadership", "leadership")):
        items = sorted(chosen.get(kind, []), key=_recency_key, reverse=True)
        entries = [_entry(i, tailored.get(i.ref, {}).get("bullets", [])) for i in items]
        if entries:
            sections.append({"key": key, "title": SECTION_TITLES[key], "type": "entries", "entries": entries})
    certs = chosen.get("certification", [])
    if certs:
        sections.append({"key": "certifications", "title": SECTION_TITLES["certifications"], "type": "bullets",
                         "bullets": [f"{c.title}" + (f" – {c.org}" if c.org and c.org.lower() not in c.title.lower() else "") for c in certs], "refs": [c.ref for c in certs]})
    lines = R.group_achievements(sorted(chosen.get("achievement", []), key=lambda i: i.start.toordinal() if i.start else 0, reverse=True))
    if lines:
        sections.append({"key": "achievements", "title": SECTION_TITLES["achievements"], "type": "lines", "lines": lines, "refs": [a.ref for a in chosen["achievement"]]})
    ranked = R.rank_skills(pl.skills, analysis["keywords"])
    groups: dict[str, list[str]] = {"Technical": [], "Concepts": [], "Soft Skills": []}
    for s in ranked:
        if len(groups[s["group"]]) < SKILL_CAPS[s["group"]]:
            groups[s["group"]].append(s["name"])
    skill_lines = [{"label": g, "text": ", ".join(groups[g])} for g in ORDER.get(analysis["role_type"], ORDER["general"]) if groups[g]]
    if skill_lines:
        sections.append({"key": "skills", "title": SECTION_TITLES["skills"], "type": "lines", "lines": skill_lines})
    return {"header": {"name": pl.name, "contacts": pl.contacts}, "sections": sections}


# ---------------------------------------------------------------- fitting to one page
def _removals(content: dict[str, Any], scores: dict[str, dict[str, Any]]) -> list[tuple[float, str, tuple]]:
    """All things we may remove, with a priority (lowest goes first)."""
    out: list[tuple[float, str, tuple]] = []
    for si, sec in enumerate(content["sections"]):
        key = sec["key"]
        if key == "entries" or sec["type"] == "entries":
            if key == "education":
                continue
            keep_min = 1 if key in ("experience", "projects") else 0
            for ei, e in enumerate(sec["entries"]):
                sc = scores.get(e.get("source", {}).get("ref", ""), {}).get("score", 50)
                if len(e["bullets"]) > 1:
                    out.append((sc + 15, "bullet", (si, ei)))
                if len(sec["entries"]) > keep_min:
                    out.append((sc + {"experience": 30, "projects": 20, "leadership": 0}.get(key, 10), "entry", (si, ei)))
        elif key == "certifications":
            for bi, ref in enumerate(sec.get("refs", [])):
                out.append((scores.get(ref, {}).get("score", 50) - 5, "cert", (si, bi)))
        elif key == "achievements":
            if len(sec.get("refs", [])) > 1:
                out.append((-4, "ach", (si, -1)))
        elif key == "skills":
            for li, ln in enumerate(sec["lines"]):
                if ln["text"].count(",") >= 4:
                    out.append((-10 + li, "skill", (si, li)))
    return sorted(out, key=lambda r: r[0])


def _apply(content: dict[str, Any], kind: str, where: tuple, scores: dict[str, dict[str, Any]], removed: list[str]) -> None:
    si, idx = where
    sec = content["sections"][si]
    if kind == "bullet":
        sec["entries"][idx]["bullets"].pop()
    elif kind == "entry":
        removed.append(sec["entries"][idx].get("source", {}).get("ref", ""))
        sec["entries"].pop(idx)
    elif kind == "cert":
        removed.append(sec["refs"].pop(idx)); sec["bullets"].pop(idx)
    elif kind == "ach":
        ref = min(sec["refs"], key=lambda r: scores.get(r, {}).get("score", 0))
        removed.append(ref)
        sec["refs"].remove(ref)
        # rebuild the grouped lines without the dropped achievement
        content["_ach_dropped"] = content.get("_ach_dropped", []) + [ref]
    elif kind == "skill":
        parts = [p.strip() for p in sec["lines"][idx]["text"].split(",")]
        sec["lines"][idx]["text"] = ", ".join(parts[:-1])


def fit_one_page(content: dict[str, Any], scores: dict[str, dict[str, Any]], items_by_ref: dict[str, P.Item] | None = None) -> tuple[dict[str, Any], list[str]]:
    """Trim the lowest-value content until the page fits at normal size. Returns (content, removed refs)."""
    content = copy.deepcopy(content)
    removed: list[str] = []
    for _ in range(80):
        if layout.measure_at(content, 1.0)["fits"]:
            break
        rem = _removals(content, scores)
        if not rem:
            break
        _, kind, where = rem[0]
        if kind == "ach":
            sec = content["sections"][where[0]]
            ref = min(sec["refs"], key=lambda r: scores.get(r, {}).get("score", 0))
            sec["refs"].remove(ref); removed.append(ref)
            if items_by_ref:
                kept = [items_by_ref[r] for r in sec["refs"] if r in items_by_ref]
                sec["lines"] = R.group_achievements(kept)
            continue
        _apply(content, kind, where, scores, removed)
    content.pop("_ach_dropped", None)
    return content, removed


# ---------------------------------------------------------------- generation
def _selection_meta(chosen_refs: set[str], items: list[P.Item], scores: dict[str, dict[str, Any]], tailored: dict[str, dict[str, Any]], analysis: dict[str, Any], pl: P.Pool, removed: list[str]) -> dict[str, Any]:
    by_ref = {i.ref: i for i in items}
    def row(ref: str) -> dict[str, Any]:
        i, s = by_ref[ref], scores[ref]
        return {"ref": ref, "kind": i.kind, "title": i.title, "org": i.org, "score": s["score"], "reasons": s["reasons"], "matched": s["matched"],
                "flags": tailored.get(ref, {}).get("flags", []), "source": tailored.get(ref, {}).get("source")}
    included = sorted((r for r in chosen_refs if r in by_ref), key=lambda r: -scores[r]["score"])
    excluded = sorted((r for r in by_ref if r not in chosen_refs), key=lambda r: -scores[r]["score"])
    profile_text = (" ".join(i.text for i in items) + " " + " ".join(s["name"] for s in pl.skills)).lower()
    found = [k for k in analysis["keywords"] if k.lower() in profile_text]
    gaps = [k for k in analysis["keywords"] if k.lower() not in profile_text]
    return {"included": [row(r) for r in included], "excluded": [row(r) for r in excluded[:14]], "trimmed_for_space": [r for r in removed if r in by_ref],
            "keywords_found": found[:25], "keywords_missing": gaps[:20]}


def generate_content(db: Session, user: User, job_title: str, company: str | None, jd: str | None) -> dict[str, Any]:
    pl = P.load(db, user)
    if not pl.profile_ok:
        raise ValueError("Your profile has no education, experience, projects or skills yet. Add them in Settings or by importing your resume first.")
    analysis = R.analyse_jd(db, job_title, company, jd)
    scores = R.score_items(pl.items, analysis, job_title, jd or "")
    caps_plus = {k: v + EXTRA for k, v in R.CAPS.items()}
    chosen: dict[str, list[P.Item]] = {}
    for kind, cap in caps_plus.items():
        ranked = sorted([i for i in pl.items if i.kind == kind], key=lambda i: -scores[i.ref]["score"])
        if kind == "project":
            # at most 3, and only those that resonate with the job (>= 60% of the best project's score)
            ranked = ranked[: R.CAPS["project"]]
            if ranked:
                floor = 0.6 * scores[ranked[0].ref]["score"]
                ranked = [i for n, i in enumerate(ranked) if n == 0 or scores[i.ref]["score"] >= floor]
            chosen[kind] = ranked
            continue
        chosen[kind] = ranked[:cap]
    to_tailor = [i for k in ("experience", "project", "leadership") for i in chosen[k]]
    tailored = T.tailor(db, to_tailor, analysis, job_title, company)
    content = build_content(pl, chosen, tailored, analysis)
    by_ref = {i.ref: i for i in pl.items}
    content, removed = fit_one_page(content, scores, by_ref)
    still = {e["source"]["ref"] for s in content["sections"] if s["type"] == "entries" for e in s["entries"] if e.get("source", {}).get("ref") and not e["source"]["ref"].startswith("education")}
    still |= {r for s in content["sections"] for r in s.get("refs", [])}
    meta = _selection_meta(still, pl.items, scores, tailored, analysis, pl, removed)
    meta["ai_tailored"] = any(t["source"] == "gemini" for t in tailored.values())
    return {"content": content, "analysis": analysis, "selection": meta, "role_type": analysis["role_type"]}


def create_version(db: Session, user: User, job_title: str, company: str | None, jd: str | None) -> ResumeVersion:
    out = generate_content(db, user, job_title.strip(), (company or "").strip() or None, (jd or "").strip() or None)
    v = ResumeVersion(user_id=user.id, title=f"{job_title.strip()}" + (f" at {company.strip()}" if company and company.strip() else ""), job_title=job_title.strip()[:160],
                      company=(company or "").strip()[:160] or None, job_description=(jd or "").strip() or None, role_type=out["role_type"], analysis=out["analysis"],
                      content=out["content"], selection=out["selection"], edited=False, model=settings.GEMINI_MODEL if out["selection"].get("ai_tailored") else None)
    db.add(v)
    db.flush()
    return v


def regenerate(db: Session, user: User, v: ResumeVersion) -> ResumeVersion:
    out = generate_content(db, user, v.job_title, v.company, v.job_description)
    v.role_type, v.analysis, v.content, v.selection, v.edited = out["role_type"], out["analysis"], out["content"], out["selection"], False
    v.model = settings.GEMINI_MODEL if out["selection"].get("ai_tailored") else None
    db.flush()
    return v


# ---------------------------------------------------------------- swapping a candidate in or out
def candidates(db: Session, user: User, v: ResumeVersion) -> list[dict[str, Any]]:
    pl = P.load(db, user)
    scores = R.score_items(pl.items, v.analysis, v.job_title, v.job_description or "")
    included = {s["ref"] for s in v.selection.get("included", [])}
    cur = {e.get("source", {}).get("ref") for s in v.content.get("sections", []) for e in s.get("entries", [])} | {r for s in v.content.get("sections", []) for r in s.get("refs", [])}
    return sorted([{"ref": i.ref, "kind": i.kind, "title": i.title, "org": i.org, "score": scores[i.ref]["score"], "reasons": scores[i.ref]["reasons"], "included": i.ref in cur or i.ref in included}
                   for i in pl.items], key=lambda r: (-r["score"]))


def swap(db: Session, user: User, v: ResumeVersion, remove_ref: str | None, add_ref: str) -> ResumeVersion:
    pl = P.load(db, user)
    by_ref = {i.ref: i for i in pl.items}
    if add_ref not in by_ref:
        raise LookupError("That item is not in your profile.")
    item = by_ref[add_ref]
    scores = R.score_items(pl.items, v.analysis, v.job_title, v.job_description or "")
    content = copy.deepcopy(v.content)
    key = {"experience": "experience", "project": "projects", "leadership": "leadership"}.get(item.kind)
    if key is None:
        raise ValueError("Only experience, projects and leadership entries can be swapped here. Edit certifications, achievements and skills directly.")
    tailored = T.tailor(db, [item], v.analysis, v.job_title, v.company)
    new_entry = _entry(item, tailored[item.ref]["bullets"])
    sec = next((s for s in content["sections"] if s["key"] == key), None)
    if sec is None:
        sec = {"key": key, "title": SECTION_TITLES[key], "type": "entries", "entries": []}
        order = list(SECTION_TITLES)
        content["sections"].append(sec)
        content["sections"].sort(key=lambda s: order.index(s["key"]) if s["key"] in order else 99)
    if any(e.get("source", {}).get("ref") == add_ref for e in sec["entries"]):
        raise ValueError("That item is already on the resume.")
    if remove_ref:
        idx = next((i for i, e in enumerate(sec["entries"]) if e.get("source", {}).get("ref") == remove_ref), None)
        if idx is None:
            raise LookupError("The item to replace is not on the resume.")
        sec["entries"][idx] = new_entry
    else:
        sec["entries"].append(new_entry)
    v.content = content
    sel = copy.deepcopy(v.selection)
    sel["included"] = [s for s in sel.get("included", []) if s["ref"] != remove_ref] + [{"ref": add_ref, "kind": item.kind, "title": item.title, "org": item.org, "score": scores[add_ref]["score"],
                                                                                      "reasons": scores[add_ref]["reasons"], "matched": scores[add_ref]["matched"], "flags": tailored[item.ref]["flags"], "source": tailored[item.ref]["source"]}]
    v.selection, v.edited = sel, True
    db.flush()
    return v


# ---------------------------------------------------------------- manual edits
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _s(x: Any, n: int = 700) -> str:
    return _CTRL.sub("", str(x if x is not None else ""))[:n].strip()


def sanitize(content: dict[str, Any]) -> dict[str, Any]:
    """Accept only the known structure, cap sizes, strip control characters."""
    h = content.get("header", {})
    out: dict[str, Any] = {"header": {"name": _s(h.get("name"), 120), "contacts": [_s(c, 120) for c in (h.get("contacts") or [])[:6] if _s(c, 120)]}, "sections": []}
    for sec in (content.get("sections") or [])[:10]:
        t = sec.get("type", "entries")
        if t not in ("entries", "bullets", "lines"):
            continue
        s: dict[str, Any] = {"key": _s(sec.get("key"), 30) or "custom", "title": _s(sec.get("title"), 60), "type": t}
        if t == "entries":
            s["entries"] = [{"title": _s(e.get("title"), 300), "right": _s(e.get("right"), 60), "subtitle": _s(e.get("subtitle"), 300), "subright": _s(e.get("subright"), 80),
                             "bullets": [_s(b, 600) for b in (e.get("bullets") or [])[:6] if _s(b, 600)], "source": e.get("source") if isinstance(e.get("source"), dict) else {}} for e in (sec.get("entries") or [])[:12]]
        elif t == "bullets":
            s["bullets"] = [_s(b, 400) for b in (sec.get("bullets") or [])[:8] if _s(b, 400)]
            if isinstance(sec.get("refs"), list):
                s["refs"] = [_s(r, 40) for r in sec["refs"][:8]]
        else:
            s["lines"] = [{"label": _s(l.get("label"), 60), "text": _s(l.get("text"), 900)} for l in (sec.get("lines") or [])[:8] if _s(l.get("text"), 900)]
            if isinstance(sec.get("refs"), list):
                s["refs"] = [_s(r, 40) for r in sec["refs"][:12]]
        out["sections"].append(s)
    return out


def fit_info(content: dict[str, Any]) -> dict[str, Any]:
    f = layout.measure(content)
    return {"fits": f["fits"], "scale": f["scale"], "overflow_lines": f["overflow_lines"], "last_baseline": f["last_baseline"], "limit": layout.BOTTOM_LIMIT, "shrunk": f["scale"] < 1.0}


def get_version(db: Session, user: User, vid: int) -> ResumeVersion:
    v = db.scalar(select(ResumeVersion).where(ResumeVersion.id == vid, ResumeVersion.user_id == user.id))
    if v is None:
        raise LookupError("Resume not found")
    return v
