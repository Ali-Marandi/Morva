from __future__ import annotations

import pytest

from morva.security.policy import Principal, Scope, authorize, has_permission


def test_lifecycle_manager_has_write_but_not_approval():
    principal = Principal(
        user_id="lifecycle",
        role="evidence_lifecycle_manager",
        scope=Scope.PROVINCE,
        scope_id="province-1",
        mfa_verified=True,
    )
    assert has_permission(principal, "evidence.lifecycle.write")
    assert has_permission(principal, "evidence.read")
    assert not has_permission(principal, "evidence.approve")


def test_lifecycle_manager_write_requires_mfa():
    principal = Principal(
        user_id="lifecycle",
        role="evidence_lifecycle_manager",
        scope=Scope.PROVINCE,
        scope_id="province-1",
        mfa_verified=False,
    )
    with pytest.raises(Exception, match="MFA"):
        authorize(
            principal,
            "evidence.lifecycle.write",
            Scope.PROVINCE,
            privileged=True,
        )


def test_lifecycle_manager_can_write_at_own_scope():
    principal = Principal(
        user_id="lifecycle",
        role="evidence_lifecycle_manager",
        scope=Scope.PROVINCE,
        scope_id="province-1",
        mfa_verified=True,
    )
    authorize(
        principal,
        "evidence.lifecycle.write",
        Scope.PROVINCE,
        resource_scope_id="province-1",
        privileged=True,
    )
