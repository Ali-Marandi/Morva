from dataclasses import replace

import pytest

from morva.runtime.config import settings
from morva.security.policy import Principal, Scope, authorize, require_distinct_actors


def test_authorize_blocks_wrong_scope() -> None:
    principal = Principal("u1", "school_finance", Scope.SCHOOL, "school-1", True)
    with pytest.raises(Exception):
        authorize(
            principal,
            "payroll.run.create",
            Scope.SCHOOL,
            resource_scope_id="school-2",
        )


def test_separation_of_duties_rejects_duplicate_actor() -> None:
    with pytest.raises(Exception):
        require_distinct_actors(["creator", "reviewer", "creator"])


def test_production_settings_fail_closed_without_oidc() -> None:
    production = replace(
        settings,
        environment="production",
        database_url="postgresql+psycopg://db",
        require_mfa=True,
        integrations_enabled=True,
        oidc_issuer="",
        oidc_audience="",
        oidc_jwks_url="",
        allow_demo_policies=False,
        require_migrated_schema=True,
    )
    with pytest.raises(RuntimeError, match="OIDC"):
        production.validate()
