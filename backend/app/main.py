"""Arjuna AI backend entrypoint."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.router import api_router
from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.db.session import engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN201
    configure_logging()
    logger.info("Starting %s (%s)", settings.APP_NAME, settings.ENVIRONMENT)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("PostgreSQL connection OK")
    except SQLAlchemyError as exc:
        # The API still boots so /health can report the problem clearly.
        logger.error("PostgreSQL connection FAILED: %s", exc)
    settings.resume_dir.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version="1.0.0",
    description=(
        "Student-facing career readiness platform. Phase 1 covers authentication, "
        "onboarding, resume analysis, role-based scoring and the student dashboard."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_timing_header(request: Request, call_next):  # noqa: ANN001, ANN201
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Flatten Pydantic errors into messages a form can display."""
    errors: list[dict[str, Any]] = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part != "body"]
        errors.append(
            {
                "field": ".".join(location) or "request",
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type"),
            }
        )
    first = errors[0]["message"] if errors else "Invalid request."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": first, "errors": errors},
    )


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "The database is unavailable or rejected the request. "
            "Check DATABASE_URL and that migrations have been applied."
        },
    )


@app.get("/health", tags=["system"])
def health() -> dict[str, Any]:
    """Liveness plus a real database check."""
    db_ok = True
    db_error: str | None = None
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        db_ok = False
        db_error = str(exc.__class__.__name__)

    return {
        "status": "ok" if db_ok else "degraded",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "database": {"connected": db_ok, "error": db_error},
        # Reported so the UI never claims an AI feature that is not configured.
        "ai_analysis": "llm_assisted" if settings.llm_enabled else "rule_based",
    }


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "name": f"{settings.APP_NAME} API",
        "docs": "/docs",
        "health": "/health",
        "api_prefix": settings.API_PREFIX,
    }


app.include_router(api_router, prefix=settings.API_PREFIX)
