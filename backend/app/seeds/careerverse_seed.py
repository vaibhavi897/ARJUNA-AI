"""Seed CareerVerse careers, stories and sources.

    python -m app.seeds.careerverse_seed
"""

from __future__ import annotations

from app.core.logging_config import configure_logging, get_logger
from app.db.session import SessionLocal
from app.modules.careerverse.career_data_service import seed_careers

logger = get_logger(__name__)


def main() -> None:
    configure_logging()
    with SessionLocal() as db:
        result = seed_careers(db)
    logger.info("CareerVerse seed complete: %s", result)
    print(result)


if __name__ == "__main__":
    main()
