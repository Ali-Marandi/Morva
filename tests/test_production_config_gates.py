from morva.runtime.config import Settings


def _production_settings(**overrides) -> Settings:
    values = {
        "environment": "production",
        "database_url": "postgresql+psycopg://morva:secret@db/morva",
        "require_mfa": True,
        "integrations_enabled": True,
        "oidc_issuer": "https://issuer.example",
        "oidc_audience": "morva",
        "oidc_jwks_url": "https://issuer.example/.well-known/jwks.json",
        "allow_demo_policies": False,
        "require_migrated_schema": True,
        "field_encryption_key": "field-key",
        "field_lookup_hmac_key": "lookup-key",
        "key_version": "v2",
    }
    values.update(overrides)
    return Settings(**values)


def test_valid_production_configuration_passes() -> None:
    _production_settings().validate()


def test_production_rejects_sqlite() -> None:
    settings = _production_settings(database_url="sqlite:///./unsafe.db")
    try:
        settings.validate()
    except RuntimeError as exc:
        assert "SQLite" in str(exc)
    else:
        raise AssertionError("production must reject SQLite")


def test_production_rejects_disabled_mfa_integrations_demo_and_missing_oidc() -> None:
    cases = [
        (dict(require_mfa=False), "MFA"),
        (dict(integrations_enabled=False), "integrations"),
        (dict(allow_demo_policies=True), "Demo"),
        (dict(oidc_jwks_url=""), "OIDC"),
        (dict(field_encryption_key=""), "encryption"),
    ]
    for overrides, expected in cases:
        settings = _production_settings(**overrides)
        try:
            settings.validate()
        except RuntimeError as exc:
            assert expected.lower() in str(exc).lower()
        else:
            raise AssertionError(f"production gate did not reject {expected}")
