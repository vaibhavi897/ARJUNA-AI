"""Spaced repetition (SM-2 variant) with a user-adjustable interval scale."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

MIN_EASE = 1.3
MAX_INTERVAL = 365


@dataclass
class SrsState:
    ease: float = 2.5
    interval_days: int = 1
    repetitions: int = 0
    lapses: int = 0


def quality_from_accuracy(accuracy: float) -> int:
    """Map a 0..1 assessment accuracy to SM-2 quality 0..5."""
    if accuracy >= 0.92:
        return 5
    if accuracy >= 0.78:
        return 4
    if accuracy >= 0.6:
        return 3
    if accuracy >= 0.4:
        return 2
    if accuracy >= 0.2:
        return 1
    return 0


def review(state: SrsState, quality: int, scale: float = 1.0) -> SrsState:
    """Return the next state. ``scale`` < 1 shortens intervals (more frequent revision)."""
    quality = max(0, min(5, quality))
    scale = max(0.5, min(2.0, scale))
    ease = max(MIN_EASE, state.ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    if quality < 3:  # lapse: start again tomorrow
        return SrsState(ease=max(MIN_EASE, ease - 0.1), interval_days=1, repetitions=0, lapses=state.lapses + 1)
    reps = state.repetitions + 1
    if reps == 1:
        interval = 1
    elif reps == 2:
        interval = 6
    else:
        interval = round(state.interval_days * ease)
    interval = max(1, min(MAX_INTERVAL, round(interval * scale)))
    return SrsState(ease=ease, interval_days=interval, repetitions=reps, lapses=state.lapses)


def due_date(today: dt.date, state: SrsState) -> dt.date:
    return today + dt.timedelta(days=state.interval_days)
