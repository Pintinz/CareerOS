from app.core.config import Settings


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


def test_postgres_database_url_is_not_flagged() -> None:
    settings = Settings(database_url="postgresql+asyncpg://user:pass@db-host:5432/careeros")
    assert not any("DATABASE_URL" in item for item in settings.uses_insecure_defaults)


def test_is_production_reads_environment_case_insensitively() -> None:
    assert Settings(environment="Production").is_production
    assert not Settings(environment="development").is_production
