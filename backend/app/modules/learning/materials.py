"""AI-generated study materials. Nothing is hardcoded: each request goes to Gemini,
the response is schema-validated, then saved so it can be reopened without re-spending."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import GeneratedMaterial, User
from app.modules.learning import ai, events, skill_gap

LEVELS = ("beginner", "intermediate", "advanced")
DEPTHS = ("brief", "standard", "deep")
ACTIONS = ("simplify", "deeper", "examples", "implementation", "diagram", "regenerate")


def learner_context(db: Session, user: User) -> str:
    text, f = skill_gap.profile_text(db, user)
    bits = []
    if f["skills"]:
        bits.append("Skills: " + ", ".join(f["skills"][:15]))
    if f["education_text"]:
        bits.append("Education: " + f["education_text"][:150])
    return "; ".join(bits)


def _save(db: Session, user: User, topic: str, level: str, depth: str, kind: str, content: dict[str, Any], parent_id: int | None = None, task_id: int | None = None) -> GeneratedMaterial:
    m = GeneratedMaterial(user_id=user.id, topic=topic[:200], level=level, depth=depth, kind=kind, content=content, parent_id=parent_id, task_id=task_id, model=settings.GEMINI_MODEL)
    db.add(m)
    db.flush()
    events.log(db, user.id, "material_generated", "material", m.id, topic=topic, level=level, kind=kind)
    return m


def generate(db: Session, user: User, topic: str, level: str, depth: str, task_id: int | None = None, force: bool = False) -> GeneratedMaterial:
    if not force:
        existing = db.scalar(select(GeneratedMaterial).where(GeneratedMaterial.user_id == user.id, GeneratedMaterial.topic == topic[:200], GeneratedMaterial.level == level, GeneratedMaterial.depth == depth, GeneratedMaterial.kind == "notes").order_by(GeneratedMaterial.id.desc()))
        if existing:
            return existing
    content = ai.material(topic, level, depth, learner_context(db, user))
    return _save(db, user, topic, level, depth, "notes", content, task_id=task_id)


def transform(db: Session, user: User, source: GeneratedMaterial, action: str) -> GeneratedMaterial:
    if action == "diagram":
        content = ai.diagram(source.topic, source.level)
        return _save(db, user, source.topic, source.level, source.depth, "diagram", content, parent_id=source.id)
    level, depth, extra = source.level, source.depth, ""
    if action == "simplify":
        level, depth, extra = "beginner", "brief", "Explain as simply as possible: plain words, everyday analogies, no jargon without a definition."
    elif action == "deeper":
        depth, extra = "deep", "Go deeper: internals, edge cases, trade-offs and advanced usage."
        level = "advanced" if source.level != "advanced" else "advanced"
    elif action == "examples":
        extra = "Focus on many varied, fully worked examples (easy to hard) with step-by-step reasoning."
    elif action == "implementation":
        extra = "Focus on practical implementation: complete runnable code, project structure, and how to test it."
    elif action != "regenerate":
        raise ValueError("Unknown action")
    content = ai.material(source.topic, level, depth, learner_context(db, user), extra, base=None if action == "regenerate" else source.content)
    return _save(db, user, source.topic, level, depth, "notes", content, parent_id=source.id)


def ask(db: Session, user: User, material: GeneratedMaterial, question: str) -> dict[str, str]:
    answer = ai.follow_up(material.topic, material.level, material.content, question)
    entry = {"question": question[:800], "answer": answer}
    material.followups = [*material.followups, entry]
    events.log(db, user.id, "material_followup", "material", material.id)
    db.flush()
    return entry


def out(m: GeneratedMaterial) -> dict[str, Any]:
    return {"id": m.id, "topic": m.topic, "level": m.level, "depth": m.depth, "kind": m.kind, "content": m.content, "followups": m.followups, "parent_id": m.parent_id, "task_id": m.task_id, "model": m.model, "created_at": m.created_at.isoformat() if m.created_at else None}
