from dataclasses import replace

import pytest

from morva.runtime.config import settings


def test_production_requires_versioned_key_rings() -> None:
    production = replace(
        settings,
        environment="production",
        database_url="postgresql+psycopg://user:pass@host/db",
        integrations_enabled=True,
        oidc_issuer="https://issuer.example",
        oidc_audience="morva-api",
        oidc_jwks_url="https://issuer.example/jwks.json",
        allow_demo_policies=False,
        require_migrated_schema=False,
        field_encryption_keys="",
        field_lookup_hmac_keys="",
        field_encryption_key="",
        field_lookup_hmac_key="",
        key_version="v1",
        key_retention_days=90,
    )

    with pytest.raises(RuntimeError, match="versioned managed encryption and lookup key rings"):
        production.validate()


def test_development_can_use_legacy_single_key_compatibility() -> None:
    development = replace(
        settings,
        environment="development",
        field_encryption_key="A" * 32,
        field_lookup_hmac_key="B" * 32,
        field_encryption_keys="",
        field_lookup_hmac_keys="",
        key_version="v1",
    )

    ring = development.managed_key_ring
    assert ring.active_version == "v1"
