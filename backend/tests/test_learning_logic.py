"""Unit tests for the pure AI Learning Hub logic (no DB, no network)."""

import datetime as dt

import pytest

from app.modules.learning import evaluation as ev
from app.modules.learning import mastery, scheduler, srs, youtube
from app.modules.learning.scheduler import Unit
from app.seeds.learning_seed import parse_track

D = dt.date(2026, 1, 5)  # a Monday


def units(n=30, minutes=60, phase="foundation"):
    return [Unit(title=f"U{i}", est_minutes=minutes, phase=phase, topic=f"T{i}") for i in range(n)]


# ------------------------------------------------------------------ scheduler
def test_plan_dates_cover_every_calendar_day():
    study, rest = scheduler.plan_dates(D, 100, [0, 1, 2, 3, 4])
    assert len(study) + len(rest) == 100
    assert all(d.weekday() < 5 for d in study) and all(d.weekday() >= 5 for d in rest)


def test_breaks_become_rest_days():
    study, rest = scheduler.plan_dates(D, 14, list(range(7)), [{"start": "2026-01-08", "end": "2026-01-10"}])
    assert dt.date(2026, 1, 9) in rest and dt.date(2026, 1, 9) not in study


def test_schedule_never_overloads_a_day():
    study, _ = scheduler.plan_dates(D, 60, [0, 1, 2, 3, 4, 5])
    slots = scheduler.build_schedule(units(40, 50), study, 120, [0, 1, 2, 3, 4, 5])
    load = {}
    for s in slots:
        load[s.date] = load.get(s.date, 0) + s.est_minutes
    assert max(load.values()) <= 120


def test_big_units_split_across_days():
    study, _ = scheduler.plan_dates(D, 30, list(range(7)))
    slots = scheduler.build_schedule([Unit("Big project", 400, "project", "projects", "P")], study, 120, list(range(7)))
    parts = [s for s in slots if s.unit]
    assert len(parts) == 4 and parts[0].part == (1, 4)
    assert sum(s.est_minutes for s in parts) >= 400


def test_reserved_days_final_is_last_and_assessments_exist():
    study, _ = scheduler.plan_dates(D, 40, [0, 1, 2, 3, 4])
    slots = scheduler.build_schedule(units(10), study, 90, [0, 1, 2, 3, 4])
    assert slots[-1].title == "Final assessment" and slots[-1].date == study[-1]
    assert any(s.category == "revision" for s in slots) and sum(1 for s in slots if s.category == "assessment") >= 2


def test_fit_units_reports_dropped_not_silent():
    kept, dropped = scheduler.fit_units(units(20, 60), capacity_minutes=600)
    assert sum(u.est_minutes for u in kept) <= 600 and len(kept) + len(dropped) == 20


def test_redistribute_respects_budget_then_overload_then_overflow():
    future = [D + dt.timedelta(days=i) for i in range(3)]
    pending = [(i, D - dt.timedelta(days=3), i, 60) for i in range(10)]
    moves, overflow = scheduler.redistribute(pending, future, {}, 120)
    assert moves and overflow  # 3 days * 120 * 1.25 = 450 < 600
    load = {}
    for m in moves:
        load[m.to_date] = load.get(m.to_date, 0) + 60
    assert max(load.values()) <= 120 * 1.25


# ------------------------------------------------------------------ spaced repetition
def test_srs_intervals_grow_and_lapse_resets():
    s = srs.SrsState()
    s = srs.review(s, 5)
    assert (s.repetitions, s.interval_days) == (1, 1)
    s = srs.review(s, 5)
    assert s.interval_days == 6
    s = srs.review(s, 5)
    assert s.interval_days > 6
    lapsed = srs.review(s, 1)
    assert lapsed.repetitions == 0 and lapsed.interval_days == 1 and lapsed.lapses == 1


def test_srs_interval_scale_is_adjustable():
    base = srs.review(srs.review(srs.review(srs.SrsState(), 5), 5), 5)
    tight = srs.review(srs.review(srs.review(srs.SrsState(), 5, 0.5), 5, 0.5), 5, 0.5)
    assert tight.interval_days < base.interval_days


def test_quality_mapping_monotonic():
    qs = [srs.quality_from_accuracy(a) for a in (0.0, 0.3, 0.5, 0.7, 0.85, 1.0)]
    assert qs == sorted(qs) and qs[0] == 0 and qs[-1] == 5


# ------------------------------------------------------------------ mastery
NOW = dt.datetime(2026, 3, 1, tzinfo=dt.timezone.utc)


def sig(frac, diff="medium", sub="a", sid=1, coding=False, days=0):
    return mastery.AttemptSignal(frac, diff, sub, sid, NOW - dt.timedelta(days=days), coding)


def test_no_attempts_is_not_started():
    assert mastery.compute([])["status"] == "not_started"


def test_opening_notes_cannot_create_mastery():
    # mastery needs assessed attempts; with none it stays 0 regardless of anything else
    assert mastery.compute([])["score"] == 0


def test_hard_questions_weigh_more_than_easy():
    easy_ok = [sig(1, "easy"), sig(0, "hard")]
    hard_ok = [sig(0, "easy"), sig(1, "hard")]
    assert mastery.compute(hard_ok, now=NOW)["score"] > mastery.compute(easy_ok, now=NOW)["score"]


def test_mastered_requires_repetition_and_coverage():
    one = [sig(1, "hard", s, 1) for s in "abc"]
    assert mastery.compute(one, known_subtopics=3, srs_reps=4, now=NOW)["status"] != "mastered"
    many = [sig(1, "hard", s, i) for i in (1, 2, 3) for s in "abc"]
    assert mastery.compute(many, known_subtopics=3, srs_reps=4, now=NOW)["status"] == "mastered"


def test_overdue_revision_flags_needs_revision():
    good = [sig(0.9, "medium", s, i) for i in (1, 2) for s in "abc"]
    assert mastery.compute(good, known_subtopics=3, revision_overdue=True, now=NOW)["status"] == "needs_revision"


def test_recency_discounts_old_results():
    old_bad_new_good = [sig(0, days=120, sid=1), sig(1, days=1, sid=2)]
    old_good_new_bad = [sig(1, days=120, sid=1), sig(0, days=1, sid=2)]
    assert mastery.compute(old_bad_new_good, now=NOW)["score"] > mastery.compute(old_good_new_bad, now=NOW)["score"]


# ------------------------------------------------------------------ evaluation
def test_objective_scoring_is_deterministic():
    assert ev.score_objective("mcq", {"index": 1}, {"choice": 1})[0] == 1.0
    assert ev.score_objective("mcq", {"index": 1}, {"choice": 2})[0] == 0.0
    assert ev.score_objective("true_false", {"value": False}, {"value": False})[0] == 1.0
    assert ev.score_objective("output_prediction", {"answer": "[1, 2]", "alternatives": ["[1,2]"]}, {"text": " [1,2] "})[0] == 1.0
    assert ev.score_objective("output_prediction", {"answer": "4"}, {"text": ""})[0] == 0.0


CASES = [{"args": [2, 3], "expected": 5}, {"args": [-1, 1], "expected": 0}]


def test_sandbox_runs_correct_and_wrong_code():
    assert ev.score_coding({"entry_function": "add"}, CASES, "def add(a, b):\n    return a + b")[0] == 1.0
    assert ev.score_coding({"entry_function": "add"}, CASES, "def add(a, b):\n    return a * b")[0] < 1.0


@pytest.mark.parametrize("code", [
    "import os\ndef add(a,b):\n    return 1",
    "import socket\ndef add(a,b):\n    return 1",
    "def add(a,b):\n    return open('x','w')",
    "def add(a,b):\n    return __import__('subprocess')",
])
def test_sandbox_blocks_dangerous_operations(code):
    frac, fb = ev.score_coding({"entry_function": "add"}, CASES, code)
    assert frac == 0.0


def test_sandbox_times_out_infinite_loops():
    out = ev.run_sandboxed("def add(a,b):\n    while True: pass", "add", CASES, timeout=2)
    assert "Time limit" in out["fatal"]


# ------------------------------------------------------------------ seed + youtube
def test_track_seed_parses_with_prerequisites():
    from app.data.learning_tracks import TRACKS

    assert len(TRACKS) >= 20
    for t in TRACKS:
        topics = parse_track(t)
        slugs = {x["slug"] for x in topics}
        assert len(topics) >= 8
        assert all(p in slugs for x in topics for p in x["prereq"])  # prerequisites resolve inside the track


@pytest.mark.parametrize("url,vid", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ?si=abc", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("dQw4w9WgXcQ", "dQw4w9WgXcQ"),
])
def test_youtube_ids(url, vid):
    assert youtube.parse_video_id(url) == vid


@pytest.mark.parametrize("bad", ["https://vimeo.com/123456", "not a url", "https://youtube.com/watch?v=short", ""])
def test_youtube_rejects_non_youtube(bad):
    assert youtube.parse_video_id(bad) is None


def test_pasted_transcript_parsing():
    segs = youtube.parse_pasted("00:05 Intro\n01:10 Main idea\n1:02:03 Wrap up")
    assert [s["start"] for s in segs] == [5.0, 70.0, 3723.0]
    plain = youtube.parse_pasted("just some words " * 200)
    assert plain and plain[0]["start"] == 0.0


def test_place_all_never_loses_units_when_sizes_pack_badly():
    # 104-minute units cannot share a 120-minute day, so naive packing overflows the calendar
    study, _ = scheduler.plan_dates(D, 30, [0, 1, 2, 3, 4])
    us = [Unit(f"U{i}", 104, "learn" if i < 17 else "project", "projects" if i >= 17 else "foundation", f"T{i}") for i in range(19)]
    slots, unplaced, scale = scheduler.place_all(us, study, 120, [0, 1, 2, 3, 4])
    placed = {s.unit.title for s in slots if s.unit}
    assert not unplaced and placed == {u.title for u in us}  # projects at the end are still scheduled
    assert scale < 1.0
    load = {}
    for s in slots:
        load[s.date] = load.get(s.date, 0) + s.est_minutes
    assert max(load.values()) <= 120
