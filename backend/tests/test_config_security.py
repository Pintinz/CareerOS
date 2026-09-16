import asyncio

from sqlalchemy.exc import DBAPIError
from starlette.requests import Request

from app.core.config import Settings
from app.main import database_error_handler, is_invalid_data_error


class _PgError(Exception):
    def __init__(self, sqlstate: str) -> None:
        super().__init__(sqlstate)
        self.sqlstate = sqlstate


def _request() -> Request:
    return Request({"type": "http", "method": "POST", "path": "/api/v1/x", "headers": [], "query_string": b""})


def test_postgres_string_too_long_becomes_a_clean_422_not_a_500() -> None:
    """Phase 11 §5: PostgreSQL enforces VARCHAR(n) (SQLSTATE 22001); SQLite never does."""
    exc = DBAPIError("INSERT ...", {}, _PgError("22001"))
    assert is_invalid_data_error(exc)
    response = asyncio.run(database_error_handler(_request(), exc))
    assert response.status_code == 422


def test_other_database_errors_stay_500_without_leaking_details() -> None:
    exc = DBAPIError("SELECT ...", {}, _PgError("08006"))
    assert not is_invalid_data_error(exc)
    response = asyncio.run(database_error_handler(_request(), exc))
    assert response.status_code == 500
    assert b"08006" not in response.body


def test_dev_defaults_are_flagged_insecure() -> None:
    settings = Settings(environment="development")
    assert "JWT_SECRET_KEY" in settings.uses_insecure_defaults
    assert "TOKEN_ENCRYPTION_KEYS" in settings.uses_insecure_defaults


def test_real_secrets_are_not_flagged() -> None:
    settings = Settings(
        environment="production",
        jwt_secret_key="a-real-generated-secret",
        token_encryption_keys="c29tZS1yZWFsLWZlcm5ldC1rZXktdmFsdWUtaGVyZQ==",
        database_url="postgresql+asyncpg://user:pass@db-host:5432/careeros",
    )
    assert settings.uses_insecure_defaults == []


def test_sqlite_database_url_is_flagged_insecure_in_production() -> None:
    """Phase 11 (spec §18): SQLite must never be silently used as a production database."""
    settings = Settings(
        environment="production",
        jwt_secret_key="a-real-generated-secret",
        token_encryption_keys="c29tZS1yZWFsLWZlcm5ldC1rZXktdmFsdWUtaGVyZQ==",
    )
    assert any("DATABASE_URL" in item for item in settings.uses_insecure_defaults)


def test_weak_or_missing_admin_seed_password_is_flagged() -> None:
    """Phase 11 §88: the bootstrap SUPER_ADMIN must never be created with a guessable password."""
    weak = Settings(admin_seed_email="ops@example.com", admin_seed_password="admin")
    missing = Settings(admin_seed_email="ops@example.com", admin_seed_password=None)
    strong = Settings(admin_seed_email="ops@example.com", admin_seed_password="a-long-unique-passphrase")
    assert any("ADMIN_SEED_PASSWORD" in item for item in weak.uses_insecure_defaults)
    assert any("ADMIN_SEED_PASSWORD" in item for item in missing.uses_insecure_defaults)
    assert not any("ADMIN_SEED_PASSWORD" in item for item in strong.uses_insecure_defaults)


def test_provider_kill_switches_disable_features_even_with_real_credentials() -> None:
    """Phase 11 §128: an incident kill switch must work without removing secrets."""
    creds = dict(
        google_client_id="id", google_client_secret="secret", google_redirect_uri="https://x/cb",
        microsoft_client_id="id", microsoft_client_secret="secret", microsoft_redirect_uri="https://x/cb",
    )
    assert Settings(**creds).gmail_tracking_available
    assert Settings(**creds).outlook_tracking_available
    assert not Settings(**creds, gmail_tracking_enabled=False).gmail_tracking_available
    assert not Settings(**creds, outlook_tracking_enabled=False).outlook_tracking_available
    assert not Settings(**creds, email_tracking_enabled=False).gmail_tracking_available
    assert not Settings(forward_email_enabled=False).forward_email_available


def test_postgres_database_url_is_not_flagged() -> None:
    settings = Settings(database_url="postgresql+asyncpg://user:pass@db-host:5432/careeros")
    assert not any("DATABASE_URL" in item for item in settings.uses_insecure_defaults)


def test_is_production_reads_environment_case_insensitively() -> None:
    assert Settings(environment="Production").is_production
    assert not Settings(environment="development").is_production


def test_managed_postgres_urls_get_the_async_driver() -> None:
    """Managed hosts (Render, Railway, Fly, Heroku) hand out sync `postgres(ql)://` URLs; the async
    engine and Alembic must still connect without anyone editing a URL containing a password."""
    for given in ("postgres://u:p@host:5432/db", "postgresql://u:p@host:5432/db"):
        assert Settings(database_url=given).normalized_database_url == "postgresql+asyncpg://u:p@host:5432/db"


def test_already_async_and_sqlite_urls_are_left_alone() -> None:
    for given in ("postgresql+asyncpg://u:p@host/db", "sqlite+aiosqlite:///./careeros_dev.db"):
        assert Settings(database_url=given).normalized_database_url == given
