"""Shared response primitives."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for models read straight out of SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    message: str
    detail: str | None = None


class ActionResult(BaseModel):
    """Returned by mutations so the client knows what to refetch."""

    message: str
    recalculated_roles: list[str] = []
    data: dict[str, Any] | None = None
