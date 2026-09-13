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

    # Local-disk media storage (spec §12/§74). Swap for a cloud StorageProvider implementation
    # once object storage credentials exist — see app/services/storage_provider.py.
    upload_dir: str = "uploads"
    public_base_url: str = "http://localhost:8000"

    google_client_id: str | None = None
    apple_client_id: str | None = None
    admob_app_id: str | None = None
    redis_url: str | None = None

    # Phase 8 — Smart Recruitment Email Tracking. All optional: the feature is fully architected
    # (provider interfaces, OAuth endpoints, mock provider) and usable end-to-end in dev without
    # any of these, per spec §39/§40 "do not stop development merely because production
    # credentials are absent." Availability of a specific provider is `flag AND credentials
    # present` — see EmailTrackingSettings below.
    email_tracking_enabled: bool = True
    gmail_tracking_enabled: bool = True
    outlook_tracking_enabled: bool = True
    forward_email_enabled: bool = False  # no inbound-mail provider configured yet — see §36.

    google_client_secret: str | None = None
    google_redirect_uri: str | None = None
    google_pubsub_topic: str | None = None

    microsoft_client_id: str | None = None
    microsoft_client_secret: str | None = None
    microsoft_tenant: str = "common"  # "common" supports both personal + work/school accounts.
    microsoft_redirect_uri: str | None = None
    microsoft_webhook_url: str | None = None
    microsoft_lifecycle_webhook_url: str | None = None

    forward_email_domain: str = "mail.careeros.app"

    # Fernet key (44-char urlsafe-base64) for encrypting OAuth tokens at rest (spec §16). A dev
    # default is provided so the app runs out of the box; production MUST set a real generated
    # key (`Fernet.generate_key()`) via environment/secret manager. Comma-separate multiple keys
    # (newest first) to support rotation — old ciphertexts still decrypt with a retired key.
    token_encryption_keys: str = "UuQmhsXcogUgfZv-VKXGPr1jS2C5Y0EIytlAc77syfg="  # dev-only, publicly committed on purpose — override in production.

    # First-run bootstrap only: if set and no admin_users row exists yet, one SUPER_ADMIN is
    # created with these credentials at startup. Leave unset after the first admin exists.
    admin_seed_email: str | None = None
    admin_seed_password: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def gmail_credentials_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret and self.google_redirect_uri)

    @property
    def gmail_tracking_available(self) -> bool:
        return self.email_tracking_enabled and self.gmail_tracking_enabled and self.gmail_credentials_configured

    @property
    def outlook_credentials_configured(self) -> bool:
        return bool(self.microsoft_client_id and self.microsoft_client_secret and self.microsoft_redirect_uri)

    @property
    def outlook_tracking_available(self) -> bool:
        return self.email_tracking_enabled and self.outlook_tracking_enabled and self.outlook_credentials_configured

    @property
    def forward_email_available(self) -> bool:
        # Also gated on an inbound-mail processor actually being configured — see
        # app/services/email_tracking_providers.py's ForwardEmailProvider docstring. No such
        # provider is wired up in this environment (spec §36: "do not block Phase 8").
        return self.email_tracking_enabled and self.forward_email_enabled

    @property
    def token_encryption_key_list(self) -> list[str]:
        return [k.strip() for k in self.token_encryption_keys.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
