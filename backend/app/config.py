from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    auth_rate_limit: str = "10/minute"

    password_reset_url: str = "oopai://reset-password"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_use_tls: bool = True

    @field_validator("jwt_secret_key")
    @classmethod
    def _require_strong_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be set to at least 32 characters")
        return value

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_from)


@lru_cache
def get_settings() -> Settings:
    return Settings()
