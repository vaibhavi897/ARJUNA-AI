"""Append-only learning event log and explicit feedback signals."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import LearningEvent, PersonalizationFeedback


def log(db: Session, user_id: int, event_type: str, entity: str | None = None, entity_id: int | None = None, **payload: Any) -> None:
    """Record a behaviour event. Never raises into the request path."""
    try:
        db.add(LearningEvent(user_id=user_id, event_type=event_type, entity=entity, entity_id=entity_id, payload=payload))
    except Exception:  # noqa: BLE001 - logging must not break learning flows
        pass


def feedback(db: Session, user_id: int, kind: str, ref: str | None, value: dict[str, Any]) -> None:
    db.add(PersonalizationFeedback(user_id=user_id, kind=kind, ref=ref, value=value))
