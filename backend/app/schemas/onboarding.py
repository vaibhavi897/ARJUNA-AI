"""Onboarding wizard schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class OnboardingStepInfo(BaseModel):
    step: int
    key: str
    title: str
    subtitle: str
    is_complete: bool
    is_optional: bool
    companion_message: str


class OnboardingStatusOut(BaseModel):
    current_step: int
    total_steps: int
    completed: bool
    percent_complete: int
    profile_completion: int
    steps: list[OnboardingStepInfo]
    next_route: str


class StepSaveResult(BaseModel):
    message: str
    step: int
    next_step: int
    completed: bool
    profile_completion: int
    companion_message: str
    recalculated_roles: list[str] = []
    data: dict[str, Any] | None = None
