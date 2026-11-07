"""Application configuration loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
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

    @field_validator("DEBUG", mode="before")
    @classmethod
    def _normalize_debug_environment(cls, value: object) -> object:
        """Accept deployment labels accidentally supplied through DEBUG.

        Some launch environments export ``DEBUG=release`` to describe their
        mode. Pydantic's boolean parser rejects that value before the app can
        start, so interpret known mode labels as the corresponding debug flag.
        """
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "production", "prod"}:
                return False
            if normalized in {"debug", "development", "dev"}:
                return True
        return value

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

    # --- Gemini (shared by Interview Arena, CareerVerse and the AI Learning Hub; keys stay server-side) ---
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    # Comma-separated models tried in order when the primary is overloaded or missing.
    GEMINI_FALLBACK_MODELS: str = "gemini-3.1-flash-lite,gemini-flash-latest,gemini-2.5-flash-lite"

    # --- Sarvam AI translation (server-side only; the browser never sees the key) ---
    SARVAM_API_KEY: str | None = None
    SARVAM_BASE_URL: str = "https://api.sarvam.ai"
    # mayura:v1 accepts up to ~1000 characters per call, sarvam-translate:v1 up to ~2000.
    SARVAM_TRANSLATE_MODEL: str = "mayura:v1"
    # --- Sarvam AI text-to-speech (optional; narration is hidden when unset) ---
    # bulbul:v2 is deprecated and the provider now rejects it. v3 takes up to
    # 2500 characters per call; its speakers are shubh, aditya, ritu, ashutosh,
    # priya, neha, rahul and others. Each model has its own speaker catalogue,
    # so change the model and the speaker together.
    SARVAM_TTS_MODEL: str = "bulbul:v3"
    SARVAM_TTS_SPEAKER: str = "shubh"
    SARVAM_TTS_PACE: float = 1.0

    # --- Outgoing email (optional; nothing is sent when disabled or unset) ---
    EMAIL_ALERTS_ENABLED: bool = False
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM: str | None = None
    # Optional copy of every student email, for staff oversight.
    ALERT_EMAIL_TO: str | None = None
    WHATSAPP_ENABLED: bool = False

    # --- Supabase Storage (optional; interview recording is hidden when unset) ---
    # The project is the same one DATABASE_URL points at. The service-role key is
    # server-side only and must never be sent to the browser.
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    SUPABASE_RECORDINGS_BUCKET: str = "interview-recordings"

    # --- Interview recording ---
    # A 40-minute capped-bitrate WebM lands around 180 MB; the ceiling leaves room.
    RECORDING_MAX_MB: int = 400
    RECORDING_RETENTION_DAYS: int = 30
    # How long a playback link stays valid once the report asks for one.
    RECORDING_SIGNED_URL_TTL: int = 3600

    # --- CareerVerse: optional external data. Each one is independent; the
    # module works from the seeded dataset when any of them is unset.
    ONET_USERNAME: str | None = None
    ONET_PASSWORD: str | None = None
    BLS_API_KEY: str | None = None
    ADZUNA_APP_ID: str | None = None
    ADZUNA_APP_KEY: str | None = None
    BRAVE_SEARCH_API_KEY: str | None = None

    # CareerVerse fit weights as JSON, e.g. {"technical":0.3,"education":0.2,"projects":0.2,"experience":0.2,"certifications":0.1}
    CAREER_FIT_WEIGHTS: str | None = None

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
    def gemini_enabled(self) -> bool:
        return bool(self.GEMINI_API_KEY)

    @property
    def llm_enabled(self) -> bool:
        """True only when a provider key is actually configured."""
        return bool(self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
