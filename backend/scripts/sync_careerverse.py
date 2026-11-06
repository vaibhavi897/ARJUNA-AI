"""Optional enrichment from external sources.

    python -m scripts.sync_careerverse bls     # US wages (works keyless, low quota)
    python -m scripts.sync_careerverse onet    # needs ONET_USERNAME / ONET_PASSWORD
    python -m scripts.sync_careerverse stories # Gemini stories for careers still on seed text

Every step fails soft and is safe to re-run.
"""

from __future__ import annotations

import sys

from app.core.logging_config import configure_logging
from app.db.session import SessionLocal
from app.modules.careerverse import career_salary_service, career_story_service


def main(argv: list[str]) -> int:
    configure_logging()
    steps = argv or ["bls", "onet"]
    with SessionLocal() as db:
        if "bls" in steps:
            print("bls:", career_salary_service.sync_bls_salaries(db))
        if "onet" in steps:
            print("onet:", career_salary_service.sync_onet_profiles(db))
        if "stories" in steps:
            print("stories:", career_story_service.generate_missing_stories(db))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
