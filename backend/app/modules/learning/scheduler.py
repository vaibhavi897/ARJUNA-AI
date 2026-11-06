"""Deterministic calendar scheduler.

Gemini decides *what* to learn (an ordered list of study units with sizes);
this module decides *when*, so workloads are always realistic regardless of what
the model returns. Pure functions only: no database, no network.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

MIN_SLICE_MINUTES = 25


@dataclass
class Unit:
    title: str
    est_minutes: int
    category: str = "learn"  # learn | practice | project
    phase: str = "foundation"
    topic: str | None = None
    topic_slug: str | None = None
    subtopics: list[str] = field(default_factory=list)
    objectives: list[str] = field(default_factory=list)
    assignment: str | None = None
    resources: list[dict[str, Any]] = field(default_factory=list)
    difficulty: str | None = None


@dataclass
class Slot:
    date: dt.date
    category: str
    title: str
    est_minutes: int
    phase: str | None = None
    unit: Unit | None = None
    part: tuple[int, int] | None = None  # (n, of)
    topics_covered: list[str] = field(default_factory=list)


def in_break(day: dt.date, breaks: list[dict[str, str]]) -> bool:
    for b in breaks:
        try:
            if dt.date.fromisoformat(b["start"]) <= day <= dt.date.fromisoformat(b["end"]):
                return True
        except (KeyError, ValueError):
            continue
    return False


def plan_dates(start: dt.date, duration_days: int, study_weekdays: list[int], breaks: list[dict[str, str]] | None = None) -> tuple[list[dt.date], list[dt.date]]:
    """Return (study_dates, rest_dates) across ``duration_days`` calendar days from ``start``."""
    study, rest = [], []
    wd = set(study_weekdays) or set(range(7))
    for i in range(duration_days):
        d = start + dt.timedelta(days=i)
        (study if d.weekday() in wd and not in_break(d, breaks or []) else rest).append(d)
    return study, rest


def cycle_length(study_weekdays: list[int]) -> int:
    return max(1, len(set(study_weekdays) or set(range(7))))


def learning_capacity_minutes(study_dates: list[dt.date], daily_minutes: int, study_weekdays: list[int]) -> int:
    """Minutes available for NEW learning after revision/assessment/final days are reserved."""
    n = cycle_length(study_weekdays)
    reserved = _reserved_indexes(len(study_dates), n)
    return (len(study_dates) - len(reserved)) * daily_minutes


def _reserved_indexes(total_days: int, cycle: int) -> dict[int, str]:
    """Map study-day index -> reserved kind. The last two days are final revision + final assessment."""
    reserved: dict[int, str] = {}
    if cycle >= 3:
        for k in range(cycle - 2, total_days, cycle):  # 0-based: (cycle-2)th = revision, (cycle-1)th = assessment
            reserved[k] = "revision"
            if k + 1 < total_days:
                reserved[k + 1] = "assessment"
    elif cycle >= 1:
        for k in range(cycle - 1, total_days, cycle):
            reserved[k] = "assessment"
    if total_days >= 3:
        reserved[total_days - 2] = "revision"
        reserved[total_days - 1] = "final"
    elif total_days >= 1:
        reserved[total_days - 1] = "final"
    return reserved


def fit_units(units: list[Unit], capacity_minutes: int) -> tuple[list[Unit], list[Unit]]:
    """Keep units in order until capacity is used. Returns (kept, dropped).

    Projects are the last to go; dropped units are reported to the learner, never silently lost.
    """
    total = sum(u.est_minutes for u in units)
    if total <= capacity_minutes:
        return list(units), []
    dropped: list[Unit] = []
    kept = list(units)
    order = sorted(range(len(kept)), key=lambda i: (kept[i].category == "project", -i))
    removed: set[int] = set()
    for i in order:
        if total <= capacity_minutes:
            break
        # drop from the end of the non-project list first
        removed.add(i)
        total -= kept[i].est_minutes
        dropped.append(kept[i])
    return [u for i, u in enumerate(kept) if i not in removed], list(reversed(dropped))


def build_schedule(units: list[Unit], study_dates: list[dt.date], daily_minutes: int, study_weekdays: list[int]) -> list[Slot]:
    return build_schedule_ex(units, study_dates, daily_minutes, study_weekdays)[0]


def build_schedule_ex(units: list[Unit], study_dates: list[dt.date], daily_minutes: int, study_weekdays: list[int]) -> tuple[list[Slot], list[Unit]]:
    """Place units on study dates, reserving revision/assessment/final days.

    A unit larger than one day's budget is split across consecutive learning days;
    small units share a day until the budget is full.
    """
    n = cycle_length(study_weekdays)
    reserved = _reserved_indexes(len(study_dates), n)
    slots: list[Slot] = []
    queue: list[tuple[Unit, int, int, int]] = []  # (unit, minutes, part, of)
    for u in units:
        parts = max(1, -(-u.est_minutes // daily_minutes))
        base = u.est_minutes // parts
        for p in range(parts):
            minutes = base + (u.est_minutes - base * parts if p == parts - 1 else 0)
            queue.append((u, max(MIN_SLICE_MINUTES, minutes), p + 1, parts))

    qi = 0
    covered: list[str] = []
    for idx, day in enumerate(study_dates):
        kind = reserved.get(idx)
        if kind == "revision":
            slots.append(Slot(day, "revision", "Revision: consolidate recent topics" if kind else "", min(daily_minutes, 90), phase=_phase_at(slots), topics_covered=covered[-6:]))
            continue
        if kind in ("assessment", "final"):
            slots.append(Slot(day, "assessment", "Final assessment" if kind == "final" else "Weekly assessment", min(daily_minutes, 75 if kind == "final" else 45), phase="final" if kind == "final" else _phase_at(slots), topics_covered=covered[-8:]))
            if kind == "assessment":
                covered = covered[-2:]
            continue
        budget = daily_minutes
        placed = False
        while qi < len(queue) and (budget >= MIN_SLICE_MINUTES or not placed):
            unit, minutes, part, of = queue[qi]
            if placed and minutes > budget:
                break
            title = unit.title if of == 1 else f"{unit.title} (part {part}/{of})"
            slots.append(Slot(day, unit.category, title, minutes, phase=unit.phase, unit=unit, part=(part, of) if of > 1 else None))
            if unit.topic and unit.topic not in covered:
                covered.append(unit.topic)
            budget -= minutes
            placed = True
            qi += 1
    leftover: list[Unit] = []
    for unit, *_ in queue[qi:]:
        if unit not in leftover:
            leftover.append(unit)
    return slots, leftover


def place_all(units: list[Unit], study_dates: list[dt.date], daily_minutes: int, study_weekdays: list[int]) -> tuple[list[Slot], list[Unit], float]:
    """Schedule every unit. Whole units cannot share a day if they do not fit together, so
    when units would overflow the calendar their durations are shrunk (never silently dropped)
    until everything fits. Returns (slots, units_that_still_do_not_fit, final_scale)."""
    scale = 1.0
    base = [u.est_minutes for u in units]
    for _ in range(8):
        for u, b in zip(units, base):
            u.est_minutes = max(MIN_SLICE_MINUTES, int(b * scale))
        slots, leftover = build_schedule_ex(units, study_dates, daily_minutes, study_weekdays)
        if not leftover:
            return slots, [], scale
        scale *= 0.88
    # last resort: report what still cannot be placed
    return slots, leftover, scale


def _phase_at(slots: list[Slot]) -> str | None:
    for s in reversed(slots):
        if s.phase:
            return s.phase
    return None


@dataclass
class Move:
    task_id: int
    from_date: dt.date
    to_date: dt.date


def redistribute(
    pending: list[tuple[int, dt.date, int, int]],
    future_dates: list[dt.date],
    load: dict[dt.date, int],
    daily_minutes: int,
    overload: float = 1.25,
) -> tuple[list[Move], list[int]]:
    """Reassign missed/pending tasks to future dates, earliest first.

    ``pending`` rows are (task_id, original_date, position, minutes) in priority order.
    First pass respects the daily budget; a second pass allows a modest overload
    (``overload`` x budget) so the deadline can still be met. Tasks that fit
    nowhere are returned as ``overflow`` so the learner can be told before anything changes.
    """
    load = dict(load)
    moves: list[Move] = []
    overflow: list[int] = []
    for task_id, orig, _pos, minutes in sorted(pending, key=lambda r: (r[1], r[2])):
        target = next((d for d in future_dates if load.get(d, 0) + minutes <= daily_minutes), None)
        if target is None:
            target = next((d for d in future_dates if load.get(d, 0) + minutes <= daily_minutes * overload), None)
        if target is None:
            overflow.append(task_id)
            continue
        load[target] = load.get(target, 0) + minutes
        moves.append(Move(task_id, orig, target))
    return moves, overflow
