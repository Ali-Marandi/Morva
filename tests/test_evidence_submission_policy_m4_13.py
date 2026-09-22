from __future__ import annotations

from datetime import datetime, timezone

import pytest

from morva.security.policy import Principal, Scope, authorize, has_permission


NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)


def test_evidence_submitter_has_submit_but_not_approve():
    principal = Principal(
        user_id="submitter",
        role="evidence_submitter",
        scope=Scope.PROVINCE,
        scope_id="province-1",
        mfa_verified=True,
    )
    assert has_permission(principal, "evidence.submit")
    assert not has_permission(principal, "evidence.approve")


def test_evidence_approver_requires_mfa():
    principal = Principal(
        user_id="approver",
        role="evidence_approver",
        scope=Scope.PROVINCE,
        scope_id="province-1",
        mfa_verified=False,
    )
    with pytest.raises(Exception, match="MFA"):
        authorize(
            principal,
            "evidence.approve",
            Scope.PROVINCE,
            privileged=True,
        )


def test_evidence_approver_can_act_with_mfa_at_own_scope():
    principal = Principal(
        user_id="approver",
        role="evidence_approver",
        scope=Scope.PROVINCE,
        scope_id="province-1",
        mfa_verified=True,
    )
    authorize(
        principal,
        "evidence.approve",
        Scope.PROVINCE,
        resource_scope_id="province-1",
        privileged=True,
    )


def test_evidence_api_routes_are_registered():
    from morva.api.app import app

    paths = set(app.openapi()["paths"])
    assert "/api/v1/evidence-submissions" in paths
    assert "/api/v1/evidence-submissions/{evidence_id}" in paths
    assert "/api/v1/evidence-submissions/{evidence_id}/decision" in paths
