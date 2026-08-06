"""
Centralized configuration for the AI Job Application Platform.

Every setting used anywhere in the codebase must be declared here and
loaded from environment variables (or a `.env` file during local
development). Nothing in this project should hardcode a secret, URL,
model name, or tunable value — import `get_settings()` instead.

Usage:
    from src.shared.config.settings import get_settings
    settings = get_settings()
    settings.supabase_url
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application-wide settings. Values are resolved in this order:
    1. Actual process environment variables
    2. A `.env` file in the project root (development convenience only)
    3. The default given below (only for genuinely safe defaults —
       never a default for a secret)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Core -----------------------------------------------------------
    environment: Environment = Field(default=Environment.DEVELOPMENT)
    app_name: str = Field(default="AI Job Application Platform")
    app_version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)

    # --- API --------------------------------------------------------------
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_prefix: str = Field(default="/api/v1")
    cors_allowed_origins: str = Field(default="http://localhost:8501")

    # --- Supabase / Database ----------------------------------------------
    supabase_url: Optional[str] = Field(default=None)
    supabase_anon_key: Optional[str] = Field(default=None)
    supabase_service_role_key: Optional[str] = Field(default=None)
    supabase_storage_bucket: str = Field(default="job-platform-files")

    # SQLAlchemy connects directly to the Supabase Postgres instance.
    # Format: postgresql+psycopg://user:password@host:port/dbname
    database_url: Optional[str] = Field(default=None)
    database_pool_size: int = Field(default=5)
    database_max_overflow: int = Field(default=10)
    database_pool_timeout_seconds: int = Field(default=30)
    database_echo: bool = Field(default=False)

    # --- Logging ------------------------------------------------------------
    log_level: LogLevel = Field(default=LogLevel.INFO)
    log_dir: str = Field(default="logs")
    log_rotation: str = Field(default="10 MB")
    log_retention: str = Field(default="30 days")
    log_to_supabase: bool = Field(default=False)

    # --- Scheduler ----------------------------------------------------------
    scheduler_timezone: str = Field(default="UTC")
    scheduler_job_defaults_max_instances: int = Field(default=1)
    scheduler_misfire_grace_time_seconds: int = Field(default=3600)

    # --- Retry / Timeout defaults ---------------------------------------------
    default_retry_count: int = Field(default=3)
    default_retry_backoff_seconds: int = Field(default=5)
    default_request_timeout_seconds: int = Field(default=30)
    browser_navigation_timeout_ms: int = Field(default=30000)

    # --- AI ------------------------------------------------------------------
    ai_provider: str = Field(default="anthropic")
    anthropic_api_key: Optional[str] = Field(default=None)
    ai_model_name: str = Field(default="claude-sonnet-4-6")
    ai_max_tokens: int = Field(default=4096)
    ai_request_timeout_seconds: int = Field(default=60)

    # --- Browser Automation ----------------------------------------------------
    browser_headless: bool = Field(default=True)
    browser_type: str = Field(default="chromium")
    browser_slow_mo_ms: int = Field(default=0)
    browser_sessions_dir: str = Field(default="browser_sessions")

    # --- Dashboard --------------------------------------------------------
    dashboard_port: int = Field(default=8501)
    dashboard_refresh_seconds: int = Field(default=30)

    # --- Application thresholds -----------------------------------------------
    minimum_match_score_to_apply: float = Field(default=0.70)
    manual_review_match_score: float = Field(default=0.55)

    @field_validator("environment", mode="before")
    @classmethod
    def _normalize_environment(cls, v: object) -> object:
        if isinstance(v, str):
            return v.lower()
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION

    @property
    def is_testing(self) -> bool:
        return self.environment == Environment.TESTING

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance. Cached because Settings performs
    file/env parsing on construction and this is called frequently
    (every request, every repository instantiation).

    Tests that need to override settings should use
    `get_settings.cache_clear()` after monkeypatching environment variables.
    """
    return Settings()
