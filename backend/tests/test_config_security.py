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
    )
    assert settings.uses_insecure_defaults == []


def test_is_production_reads_environment_case_insensitively() -> None:
    assert Settings(environment="Production").is_production
    assert not Settings(environment="development").is_production
