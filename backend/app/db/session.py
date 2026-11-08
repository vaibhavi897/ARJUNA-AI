"""Engine, session factory and the FastAPI session dependency."""

from __future__ import annotations

from collections.abc import Generator

import os

from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# On Vercel every function instance would keep its own pool and quickly exhaust
# the Supabase pooler's client limit. There: no local pool (the Supabase
# transaction pooler does the pooling) and no server-side prepared statements.
_serverless = bool(os.environ.get("VERCEL"))
_engine_kwargs: dict = (
    {"poolclass": NullPool, "connect_args": {"prepare_threshold": None}}
    if _serverless
    else {"pool_pre_ping": True}
)

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
    **_engine_kwargs,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Request-scoped session. Rolls back on error, always closes."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
