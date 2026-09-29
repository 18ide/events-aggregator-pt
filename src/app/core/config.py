from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Option 1: full DATABASE_URL (used locally via .env).
    database_url: str | None = None

    # Option 2: individual POSTGRES_* variables (provided by LMS).
    postgres_connection_string: str | None = None
    postgres_host: str | None = None
    postgres_port: int | None = None
    postgres_username: str | None = None
    postgres_password: str | None = None
    postgres_database_name: str | None = None

    events_provider_url: str
    events_provider_api_key: str
    sync_interval_seconds: int = 86400

    @model_validator(mode="after")
    def _resolve_database_url(self) -> Settings:
        if self.database_url:
            return self

        if self.postgres_connection_string:
            self.database_url = _to_asyncpg_url(self.postgres_connection_string)
            return self

        required = (
            self.postgres_host,
            self.postgres_port,
            self.postgres_username,
            self.postgres_password,
            self.postgres_database_name,
        )
        if all(value is not None for value in required):
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database_name}"
            )
            return self

        raise ValueError(
            "Cannot resolve database URL: set DATABASE_URL, POSTGRES_CONNECTION_STRING, "
            "or all POSTGRES_HOST/PORT/USERNAME/PASSWORD/DATABASE_NAME"
        )


def _to_asyncpg_url(url: str) -> str:
    """Convert a plain postgres URL to one using the asyncpg driver."""
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


settings = Settings()
