from __future__ import annotations

import os
from dataclasses import dataclass


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

    @property
    def production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    def validate(self) -> None:
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

    @property
    def migrations_ready(self) -> bool:
        return os.getenv("MORVA_MIGRATIONS_READY", "false").lower() == "true"


settings = Settings()
