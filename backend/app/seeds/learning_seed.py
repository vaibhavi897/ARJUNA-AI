"""Seed AI Learning Hub reference data: tracks, topic taxonomy, prerequisites.

    python -m app.seeds.learning_seed

Seeds metadata only. No notes, quizzes, roadmaps or resource links are created.
"""

from __future__ import annotations

import re

from sqlalchemy import delete, select

from app.core.logging_config import configure_logging, get_logger
from app.data.learning_tracks import PHASES, TRACKS
from app.db.session import SessionLocal
from app.models import LearningTopic, LearningTrack

logger = get_logger(__name__)
PHASE_NAME = {"F": "foundation", "I": "intermediate", "A": "advanced"}
TOKEN = re.compile(r"^(?P<title>.+?)\s+(?P<phase>[FIA])(?P<hours>\d+)$")


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_track(track: dict) -> list[dict]:
    topics: list[dict] = []
    by_title: dict[str, str] = {}
    position = 0
    for subject, chain in track["subjects"].items():
        previous: str | None = None
        for raw in chain.split(">"):
            m = TOKEN.match(raw.strip())
            if not m:
                raise ValueError(f"{track['slug']}: cannot parse topic {raw!r}")
            slug = slugify(m["title"])
            topics.append({"slug": slug, "title": m["title"], "subject": subject, "phase": PHASE_NAME[m["phase"]], "hours": float(m["hours"]), "prereq": [previous] if previous else [], "position": position})
            by_title[m["title"]] = slug
            previous = slug
            position += 1
    for title, deps in track.get("deps", {}).items():
        target = next((t for t in topics if t["title"] == title), None)
        if target is None:
            raise ValueError(f"{track['slug']}: dep target {title!r} unknown")
        for d in deps:
            if d not in by_title:
                raise ValueError(f"{track['slug']}: dep {d!r} unknown")
            if by_title[d] not in target["prereq"]:
                target["prereq"].append(by_title[d])
    return topics


def seed(db) -> dict[str, int]:  # noqa: ANN001
    n_tracks = n_topics = 0
    for t in TRACKS:
        track = db.scalar(select(LearningTrack).where(LearningTrack.slug == t["slug"]))
        if track is None:
            track = LearningTrack(slug=t["slug"], title=t["title"], category=t["category"], description=t["description"], phases=PHASES, career_slug=t["career"])
            db.add(track)
        else:
            track.title, track.category, track.description, track.phases, track.career_slug = t["title"], t["category"], t["description"], PHASES, t["career"]
        db.flush()
        db.execute(delete(LearningTopic).where(LearningTopic.track_id == track.id))
        for topic in parse_track(t):
            db.add(LearningTopic(track_id=track.id, slug=topic["slug"], title=topic["title"], subject=topic["subject"], phase=topic["phase"], est_hours=topic["hours"], prerequisites=topic["prereq"], position=topic["position"]))
            n_topics += 1
        n_tracks += 1
    db.commit()
    return {"tracks": n_tracks, "topics": n_topics}


def main() -> None:
    configure_logging()
    with SessionLocal() as db:
        print(seed(db))


if __name__ == "__main__":
    main()
