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


settings = Settings()
