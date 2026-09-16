from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True)

    environment: str = "development"
    app_name: str = "CareerOS API"
    app_version: str = "0.1.0"

    # Falls back to local SQLite so the backend runs with no Postgres/Docker installed. Production
    # MUST set a real Postgres URL — see `uses_insecure_defaults` below, which refuses to boot a
    # production-flagged process still pointed at the SQLite fallback. Managed hosts (Render,
    # Railway, Fly, Heroku) hand out `postgres://` or `postgresql://` URLs; `normalized_database_url`
    # upgrades those to this app's async driver so the platform value can be used as-is.
    database_url: str = "sqlite+aiosqlite:///./careeros_dev.db"

    # Phase 11 — production connection pool (spec §7). Ignored for SQLite (which has no real
    # pooling concept); applied to the async engine for any other dialect. Environment-configurable
    # so a given deployment can tune it to its managed Postgres plan's connection limit without a
    # code change.
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout_seconds: int = 30
    db_pool_recycle_seconds: int = 1800  # 30 min — safely under most managed Postgres idle-close windows.
    db_pool_pre_ping: bool = True

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

    # Live discovery engine (DISCOVERY_ENGINE.md). Kill switches first: turning any of these off
    # stops automatic fetching/research without affecting manual admin content management.
    # Career-feed flag names (CAREER_SOURCE_INTEGRATION.md) are accepted as aliases of the original ones.
    web_discovery_enabled: bool = Field(default=True, validation_alias=AliasChoices("web_discovery_enabled", "career_source_sync_enabled"))
    # Group switches: every public ATS adapter (Lever, Greenhouse, Ashby, SmartRecruiters, Workday) /
    # the official-page structured-data adapter. Per-adapter flags below still apply.
    structured_ats_sync_enabled: bool = True
    html_source_sync_enabled: bool = True
    lever_discovery_enabled: bool = True
    greenhouse_discovery_enabled: bool = True
    ashby_discovery_enabled: bool = True
    # Off by default: api.smartrecruiters.com/robots.txt (checked 2026-09-14) allows only LinkedInBot
    # and disallows all other crawlers, and discovery always honours robots.txt. Enable only if that
    # changes or SmartRecruiters grants access; until then such sources fail as ROBOTS_DISALLOWED.
    smartrecruiters_discovery_enabled: bool = False
    # Workday and Oracle Recruiting career sites expose public, tenant-specific JSON (live-verified on
    # employer tenants 2026-09-15); each source is still configured and polled individually.
    workday_discovery_enabled: bool = True
    oracle_recruiting_discovery_enabled: bool = True
    rss_discovery_enabled: bool = True
    structured_page_discovery_enabled: bool = True
    # Publishing stays an editorial decision unless this AND the source's auto_publish_allowed
    # AND every verification gate pass. Never on by default.
    auto_publish_discovery: bool = Field(default=False, validation_alias=AliasChoices("auto_publish_discovery", "source_auto_publish_enabled"))
    # Consecutive complete syncs a listing must be absent before it is treated as removed at its
    # source (hidden, pending admin confirmation). Earlier misses only flag it POSSIBLY_REMOVED.
    discovery_removal_confirmations: int = Field(default=2, ge=1, le=10)

    ai_research_enabled: bool = Field(default=False, validation_alias=AliasChoices("ai_research_enabled", "ai_extraction_enabled"))
    anthropic_research_enabled: bool = False
    anthropic_api_key: str | None = None  # server-side only; never sent to clients or logged.
    # Configurable per deployment; pick a smaller model here to trade quality for cost.
    anthropic_research_model: str = "claude-opus-5"
    ai_research_max_items_per_run: int = 5
    ai_research_max_tokens_per_batch: int = 60_000
    ai_research_min_trust_level: int = 3
    ai_research_content_types: str = "JOB,INTERNSHIP,GRADUATE_PROGRAM,APPRENTICESHIP,TRAINEE_PROGRAM,SCHOLARSHIP,FELLOWSHIP,INTELLIGENCE"

    discovery_user_agent: str = "CareerOSDiscoveryBot/1.0 (+https://careeros.app/bot)"
    discovery_request_timeout_seconds: float = 20.0
    discovery_min_request_interval_seconds: float = 2.0  # per host, within a process
    discovery_max_requests_per_run: int = 60
    discovery_max_response_bytes: int = 3_000_000
    discovery_max_items_per_run: int = 500
    # "system": verify outbound discovery/logo TLS against the OS certificate store (TLS-inspecting
    # corporate proxies or antivirus). "certifi" (default): the bundled Mozilla CA list.
    outbound_tls_trust_store: Literal["certifi", "system"] = "certifi"
    discovery_dispatch_interval_minutes: int = 5
    discovery_runs_per_dispatch: int = 3
    verification_interval_hours: int = 12
    verification_max_items_per_run: int = 100

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
    def normalized_database_url(self) -> str:
        """The database URL with an async driver. Managed Postgres providers expose `postgres://`
        or `postgresql://` connection strings (psycopg's sync form); SQLAlchemy's async engine needs
        `postgresql+asyncpg://`. Rewriting here means a platform-provided value works unchanged and
        nobody has to hand-edit a URL that contains a password."""
        url = self.database_url
        if url.startswith("postgres://"):
            return "postgresql+asyncpg://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            return "postgresql+asyncpg://" + url[len("postgresql://") :]
        return url

    @property
    def uses_insecure_defaults(self) -> list[str]:
        """Which known dev-only default secrets are still active. Checked at startup — see
        `app/main.py`'s `lifespan` — to refuse to boot in production with a publicly-committed
        secret (Phase 9.5 security audit finding: nothing previously stopped this)."""
        insecure = []
        jwt_lower = self.jwt_secret_key.lower()
        if self.jwt_secret_key == "dev-only-insecure-secret-change-me" or "change-me" in jwt_lower or "changeme" in jwt_lower:
            insecure.append("JWT_SECRET_KEY")
        if "UuQmhsXcogUgfZv-VKXGPr1jS2C5Y0EIytlAc77syfg=" in self.token_encryption_key_list:
            insecure.append("TOKEN_ENCRYPTION_KEYS")
        # Phase 11 (spec §18): SQLite is a dev/test fallback only — see DATABASE.md/DEPLOYMENT.md
        # for why (no real FK enforcement guarantee at scale, no real connection pooling, single
        # file, no concurrent-writer story). A production-flagged process must never silently run
        # against it.
        if self.database_url.startswith("sqlite"):
            insecure.append("DATABASE_URL (SQLite is not a supported production database)")
        # Phase 11 (spec §18/§88): the first-admin bootstrap creates a SUPER_ADMIN, so it must never
        # run with a missing or guessable password.
        if self.admin_seed_email and (not self.admin_seed_password or len(self.admin_seed_password) < 12):
            insecure.append("ADMIN_SEED_PASSWORD (required, at least 12 characters, when ADMIN_SEED_EMAIL is set)")
        return insecure

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
    def anthropic_research_available(self) -> bool:
        """AI research needs both flags and a key; without them discovery continues through the
        structured adapters, RSS and manual ingestion (spec §77)."""
        return self.web_discovery_enabled and self.ai_research_enabled and self.anthropic_research_enabled and bool(self.anthropic_api_key)

    @property
    def ai_research_content_type_list(self) -> list[str]:
        return [t.strip().upper() for t in self.ai_research_content_types.split(",") if t.strip()]

    @property
    def token_encryption_key_list(self) -> list[str]:
        return [k.strip() for k in self.token_encryption_keys.split(",") if k.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
