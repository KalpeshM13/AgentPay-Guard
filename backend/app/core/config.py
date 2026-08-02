"""Application settings loaded from environment variables.

Uses Pydantic BaseSettings for type-safe configuration with .env file support.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Project root – resolves relative paths like ./data/agentpay.db
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Top-level application settings.

    All values can be overridden via environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -- Application ---------------------------------------------------------
    APP_NAME: str = "AgentPay Guard"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = (
        "Kill Switch & Policy-Enforced Payments for Autonomous AI Agents"
    )
    DEBUG: bool = False

    # -- Server --------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["*"]

    # -- Database ------------------------------------------------------------
    # SQLite is the default for the hackathon MVP; use aiosqlite for async.
    DATABASE_URL: str = (
        f"sqlite+aiosqlite:///{PROJECT_ROOT / 'data' / 'agentpay.db'}"
    )
    DB_ECHO: bool = False  # set True during development to see SQL queries

    # -- Firebase ------------------------------------------------------------
    FIREBASE_CREDENTIALS: str | None = None
    FIREBASE_CREDENTIALS_PATH: str | None = None

    # -- Logging -------------------------------------------------------------
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FORMAT: Literal["text", "json"] = "text"

    # -- Security ------------------------------------------------------------
    SECRET_KEY: str = "change-me-in-production"

    # -- JWT Authentication --------------------------------------------------
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # -- Default owner (created on first startup) ----------------------------
    DEFAULT_OWNER_EMAIL: str = "admin@agentpay.dev"
    DEFAULT_OWNER_PASSWORD: str = "admin123"

    # -- Policy defaults (used when creating new agents) ---------------------
    DEFAULT_PER_TRANSACTION_LIMIT: float = 1_000.0
    DEFAULT_DAILY_LIMIT: float = 5_000.0
    DEFAULT_MAX_REQUESTS_PER_MINUTE: int = 10

    # -- Pending payment window (seconds) ------------------------------------
    PENDING_DELAY_SECONDS: float = 5.0

    # -- API prefix ----------------------------------------------------------
    API_V1_PREFIX: str = "/api/v1"

    # -- Blockchain Configuration --------------------------------------------
    IS_BLOCKCHAIN_ENABLED: bool = False
    RPC_PROVIDER_URL: str = "http://127.0.0.1:8545"
    SMART_CONTRACT_ADDRESS: str | None = None
    AGENT_PRIVATE_KEY: str | None = None

    # -- AI Providers (optional — backend works without them) ----------------
    # Set to a real key to enable AI-powered explanations and summaries.
    GROQ_API_KEY: str = ""
    GROQ_DEFAULT_MODEL: str = "llama-3.1-8b-instant"
    GEMINI_API_KEY: str = ""
    GEMINI_DEFAULT_MODEL: str = "gemini-2.5-flash"


# ---------------------------------------------------------------------------
# Singleton — import this everywhere
# ---------------------------------------------------------------------------
settings = Settings()


# =============================================================================
# Production guard — warn if SECRET_KEY is still the default at startup
# =============================================================================


def validate_production_settings() -> None:
    """Log warnings for insecure production settings.

    Called once at startup by ``app/main.py``.  Does NOT raise — the app
    still starts so you can fix settings without downtime.
    """
    import logging

    logger = logging.getLogger(__name__)
    warnings: list[str] = []

    if settings.SECRET_KEY == "change-me-in-production":
        warnings.append(
            "SECRET_KEY is still the default value — "
            "generate a real key with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    if settings.DEFAULT_OWNER_PASSWORD == "admin123":
        warnings.append(
            "DEFAULT_OWNER_PASSWORD is still 'admin123' — change it in production!"
        )

    if settings.DEBUG:
        warnings.append(
            "DEBUG is True — disable it in production for security."
        )

    if "all" in map(str.lower, settings.CORS_ORIGINS) or "*" in settings.CORS_ORIGINS:
        warnings.append(
            "CORS_ORIGINS allows all origins ('*') — restrict it in production."
        )

    for w in warnings:
        logger.warning("⚠️  %s", w)

    if warnings:
        logger.warning(
            "👉  Set environment variables via your hosting dashboard "
            "(Render, Railway, etc.) or in the .env file."
        )
