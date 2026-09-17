from __future__ import annotations

import os
from dataclasses import dataclass

from morva.runtime.key_management import ManagedKeyRing, legacy_key_ring


@dataclass(frozen=True, slots=True)
class Settings:
    environment: str = os.getenv("MORVA_ENV", "development")
    database_url: str = os.getenv("MORVA_DATABASE_URL", "sqlite:///./morva.db")
    require_mfa: bool = os.getenv("MORVA_REQUIRE_MFA", "true").lower() == "true"
    integrations_enabled: bool = os.getenv("MORVA_INTEGRATIONS_ENABLED", "false").lower() == "true"
    log_level: str = os.getenv("MORVA_LOG_LEVEL", "INFO")
    oidc_issuer: str = os.getenv("MORVA_OIDC_ISSUER", "").strip()
    oidc_audience: str = os.getenv("MORVA_OIDC_AUDIENCE", "").strip()
    oidc_jwks_url: str = os.getenv("MORVA_OIDC_JWKS_URL", "").strip()
    allow_demo_policies: bool = os.getenv("MORVA_ALLOW_DEMO_POLICIES", "false").lower() == "true"
    require_migrated_schema: bool = os.getenv("MORVA_REQUIRE_MIGRATED_SCHEMA", "true").lower() == "true"
    field_encryption_key: str = os.getenv("MORVA_FIELD_ENCRYPTION_KEY", "").strip()
    field_lookup_hmac_key: str = os.getenv("MORVA_FIELD_LOOKUP_HMAC_KEY", "").strip()
    field_encryption_keys: str = os.getenv("MORVA_FIELD_ENCRYPTION_KEYS", "").strip()
    field_lookup_hmac_keys: str = os.getenv("MORVA_FIELD_LOOKUP_HMAC_KEYS", "").strip()
    key_version: str = os.getenv("MORVA_KEY_VERSION", "v1").strip()
    key_retention_days: int = int(os.getenv("MORVA_KEY_RETENTION_DAYS", "90"))

    @property
    def production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def managed_key_ring(self) -> ManagedKeyRing:
        if self.field_encryption_keys and self.field_lookup_hmac_keys:
            return ManagedKeyRing.from_environment(
                active_version=self.key_version,
                encryption_keys=self.field_encryption_keys,
                lookup_hmac_keys=self.field_lookup_hmac_keys,
            )
        return legacy_key_ring(
            key_version=self.key_version,
            encryption_key=self.field_encryption_key,
            lookup_hmac_key=self.field_lookup_hmac_key,
        )

    def validate(self) -> None:
        if self.key_retention_days < 30:
            raise RuntimeError("Managed key retention must be at least 30 days")
        if self.production and self.database_url.startswith("sqlite"):
            raise RuntimeError("SQLite is forbidden in production; configure PostgreSQL")
        if self.production and not self.require_mfa:
            raise RuntimeError("MFA must be enabled in production")
        if self.production and not self.integrations_enabled:
            raise RuntimeError("Production integrations must be explicitly enabled")
        if self.production and not (self.oidc_issuer and self.oidc_audience and self.oidc_jwks_url):
            raise RuntimeError("Production OIDC authentication must be configured")
        if self.production and self.allow_demo_policies:
            raise RuntimeError("Demo policies are forbidden in production")
        if self.production and self.require_migrated_schema and not self.migrations_ready:
            raise RuntimeError("Production requires a migrated database schema")
        if self.production:
            if not (self.field_encryption_keys and self.field_lookup_hmac_keys):
                raise RuntimeError("Production requires versioned managed encryption and lookup key rings")
            self.managed_key_ring

    @property
    def migrations_ready(self) -> bool:
        return os.getenv("MORVA_MIGRATIONS_READY", "false").lower() == "true"


settings = Settings()
