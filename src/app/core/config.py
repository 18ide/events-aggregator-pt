from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Локально: DATABASE_URL из .env
    database_url: str | None = None

    # В LMS: POSTGRES_*
    postgres_connection_string: str | None = None
    postgres_host: str | None = None
    postgres_port: int | None = None
    postgres_username: str | None = None
    postgres_password: str | None = None
    postgres_database_name: str | None = None

    events_provider_url: str
    events_provider_api_key: str
    sync_interval_seconds: int = 86400

    outbox_poll_interval_seconds: int = 5
    outbox_batch_size: int = 10
    outbox_max_attempts: int = 10

    capashino_url: str
    capashino_api_key: str

    glitchtip_dsn: str | None = None

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
        if all(v is not None for v in required):
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_username}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database_name}"
            )
            return self

        raise ValueError(
            "Cannot resolve database URL: set DATABASE_URL, POSTGRES_CONNECTION_STRING, "
            "or all POSTGRES_* variables"
        )


def _to_asyncpg_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


settings = Settings()
