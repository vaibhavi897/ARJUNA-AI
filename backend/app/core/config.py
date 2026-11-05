"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings. Every value is overridable through the environment."""

    model_config = SettingsConfigDict(
        env_file=str(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Core ---
    APP_NAME: str = "Arjuna AI"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_PREFIX: str = "/api"

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/arjuna_ai"
    )
    DB_ECHO: bool = False

    # --- Auth ---
    JWT_SECRET: str = "CHANGE_ME_INSECURE_DEV_SECRET"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- CORS / frontend ---
    # Kept as a plain string: pydantic-settings JSON-decodes list-typed fields
    # straight from .env before validators run, so a comma-separated value
    # would raise. Parsed by ``cors_origins`` below instead.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    FRONTEND_URL: str = "http://localhost:5173"

    # --- Uploads ---
    UPLOAD_DIR: str = str(BACKEND_DIR / "uploads")
    MAX_UPLOAD_SIZE_MB: int = 5

    # --- Optional LLM provider (qualitative analysis). Unset => deterministic only.
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    LLM_MODEL: str = "claude-opus-5"

    # --- Logging ---
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origins(self) -> list[str]:
        """Allowed browser origins. Accepts a comma-separated or JSON list."""
        raw = (self.CORS_ORIGINS or "").strip()
        if not raw:
            return [self.FRONTEND_URL]
        if raw.startswith("["):
            import json

            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return [self.FRONTEND_URL]
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [part.strip() for part in raw.split(",") if part.strip()]

    @property
    def resume_dir(self) -> Path:
        path = Path(self.UPLOAD_DIR) / "resumes"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def llm_enabled(self) -> bool:
        """True only when a provider key is actually configured."""
        return bool(self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
