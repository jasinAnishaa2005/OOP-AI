import re
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
_LIMIT = re.compile(r"^\s*(\d+)\s*(?:/|per)\s*(\d+)?\s*(second|minute|hour|day)s?\s*$")


def parse_limit(limit: str) -> tuple[int, int]:
    """'10/minute' -> (10, 60); also accepts '5 per 2 hours'."""
    match = _LIMIT.match(limit.lower())
    if not match:
        raise ValueError(f"Invalid rate limit: {limit!r}")
    amount, multiplier = int(match[1]), int(match[2] or 1)
    if amount < 1 or multiplier < 1:
        raise ValueError(f"Rate limit {limit!r} needs at least 1 request per period and a period of at least 1")
    return amount, multiplier * _PERIODS[match[3]]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "OOP-AI"
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg://oopai:oopai@localhost:5432/oopai"

    jwt_secret_key: str = Field(default="", min_length=0)
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 1
    remember_me_refresh_token_days: int = 30
    password_reset_minutes: int = 30

    cors_origins: list[str] = ["http://localhost:8081", "http://localhost:19006"]

    rate_limit_enabled: bool = True
    # Limits are stored in the database, so all workers share them. Logins count only failed attempts, per account
    # (email and student ID resolve to the same account): strictly per account and client IP, so an attacker
    # elsewhere cannot lock a student out, plus a looser cap per account across all IPs against distributed guessing.
    auth_rate_limit: str = "10/minute"
    auth_account_rate_limit: str = "100/hour"
    # Per client IP; generous because a whole campus can share one address behind NAT.
    auth_ip_rate_limit: str = "100/minute"

    password_reset_url: str = "oopai://reset-password"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True

    # AI exam generation. Keys stay on the server; the mobile app never sees them.
    ai_provider: Literal["fake", "gemini"] = "fake"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash"
    # Comma-separated models tried in order when the primary one is overloaded, rate-limited or unavailable.
    gemini_fallback_models: str = "gemini-3-flash-preview,gemini-flash-lite-latest"
    ai_timeout_seconds: int = Field(default=300, ge=1)
    ai_max_attempts: int = Field(default=3, ge=1, le=5)
    ai_retry_backoff_seconds: float = 10.0
    exam_create_rate_limit: str = "10/minute"  # per student, shared by all workers
    exam_daily_limit: int = 30

    # Recovery of exams left pending/generating by a crashed or restarted server (runs in every API worker).
    generation_recovery_enabled: bool = True
    generation_recovery_interval_seconds: float = 60.0
    generation_pending_grace_seconds: int = 120
    generation_lease_seconds: int = 900
    generation_max_runs: int = Field(default=3, ge=1)
    generation_workers: int = Field(default=2, ge=1)

    @field_validator("jwt_secret_key")
    @classmethod
    def _require_strong_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be set to at least 32 characters")
        return value

    @field_validator("auth_rate_limit", "auth_account_rate_limit", "auth_ip_rate_limit", "exam_create_rate_limit")
    @classmethod
    def _valid_rate_limit(cls, value: str) -> str:
        parse_limit(value)
        return value

    @model_validator(mode="after")
    def _no_fake_ai_in_production(self) -> "Settings":
        if self.environment == "production" and self.ai_provider == "fake":
            raise ValueError("AI_PROVIDER must be a real provider (e.g. gemini) in production")
        return self

    @property
    def gemini_fallback_model_list(self) -> tuple[str, ...]:
        return tuple(m.strip() for m in self.gemini_fallback_models.split(",") if m.strip())

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)


@lru_cache
def get_settings() -> Settings:
    return Settings()
