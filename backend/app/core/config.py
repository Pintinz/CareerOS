from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    app_name: str = "CareerOS API"
    app_version: str = "0.1.0"

    # Falls back to local SQLite so the backend runs with no Postgres/Docker installed.
    database_url: str = "sqlite+aiosqlite:///./careeros_dev.db"

    jwt_secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    cors_origins: str = "http://localhost:3000,http://localhost:8080"

    google_client_id: str | None = None
    apple_client_id: str | None = None
    gmail_oauth_client_id: str | None = None
    gmail_oauth_client_secret: str | None = None
    outlook_oauth_client_id: str | None = None
    outlook_oauth_client_secret: str | None = None
    admob_app_id: str | None = None
    redis_url: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
