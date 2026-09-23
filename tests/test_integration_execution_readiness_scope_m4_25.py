from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from morva.api.v1.integration_execution_readiness import _resolve_scope_filter
from morva.persistence.integration_execution_readiness_records import (
    IntegrationExecutionReadinessPersistenceError,
    IntegrationExecutionReadinessVerificationRecord,
    IntegrationExecutionReadinessVerificationRepository,
)
from morva.persistence.models import Base
from morva.runtime.independent_integration_execution_readiness_verifier_m4_21 import (
    IndependentIntegrationExecutionReadinessVerification,
)
from morva.runtime.integration_execution_readiness_assessment import (
    IntegrationExecutionReadinessAssessment,
)
from morva.security.policy import Principal, Scope
from morva.runtime.readiness_scope_binding_m4_25 import (
    readiness_scope_binding_fingerprint,
)


NOW = datetime(2026, 9, 23, 14, tzinfo=timezone.utc)


def _verification(candidate_sha: str = "d" * 40):
    fingerprint_payload = {
        "assessment_version": 1,
        "repository": "Ali-Marandi/Morva",
        "candidate_sha": candidate_sha,
        "target_environment": "staging",
        "checked_at": NOW.isoformat(),
        "evidence_readiness_fingerprint": "3" * 64,
        "binding_fingerprint": "1" * 64,
        "binding_verification_fingerprint": "2" * 64,
        "state": "ready",
        "blockers": [],
    }
    assessment_fingerprint = sha256(
        __import__("json").dumps(
            fingerprint_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    assessment = IntegrationExecutionReadinessAssessment(
        assessment_version=1,
        repository="Ali-Marandi/Morva",
        candidate_sha=candidate_sha,
        target_environment="staging",
        checked_at=NOW,
        evidence_readiness_fingerprint="3" * 64,
        binding_fingerprint="1" * 64,
        binding_verification_fingerprint="2" * 64,
        state="ready",
        blockers=(),
        fingerprint=assessment_fingerprint,
    )
    return IndependentIntegrationExecutionReadinessVerification(
        assessment=assessment,
        verified_at=NOW,
    )


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[IntegrationExecutionReadinessVerificationRecord.__table__],
    )
    local = sessionmaker(bind=engine, future=True)
    with local() as db:
        yield db
        db.rollback()


def test_persistence_binds_exact_scope(session):
    repository = IntegrationExecutionReadinessVerificationRepository(session)
    verification = _verification()

    record = repository.record(
        verification,
        organization_scope="district",
        organization_scope_id="district-1",
    )

    assert record.organization_scope == "district"
    assert record.organization_scope_id == "district-1"
    assert record.scope_binding_fingerprint == readiness_scope_binding_fingerprint(
        verification_fingerprint=verification.fingerprint,
        organization_scope="district",
        organization_scope_id="district-1",
    )


def test_same_verification_cannot_be_rebound_to_another_scope(session):
    repository = IntegrationExecutionReadinessVerificationRepository(session)
    verification = _verification()
    repository.record(
        verification,
        organization_scope="district",
        organization_scope_id="district-1",
    )

    with pytest.raises(
        IntegrationExecutionReadinessPersistenceError,
        match="different organization scope",
    ):
        repository.record(
            verification,
            organization_scope="district",
            organization_scope_id="district-2",
        )


def test_scope_binding_tamper_fails_closed(session):
    repository = IntegrationExecutionReadinessVerificationRepository(session)
    record = repository.record(
        _verification(),
        organization_scope="province",
        organization_scope_id="province-1",
    )
    session.flush()
    record.scope_binding_fingerprint = "f" * 64

    with pytest.raises(
        IntegrationExecutionReadinessPersistenceError,
        match="scope binding fingerprint mismatch",
    ):
        repository.latest(
            organization_scope="province",
            organization_scope_id="province-1",
        )


def test_scope_filter_is_forced_for_non_ministry_principal():
    principal = Principal(
        "district-user",
        "auditor",
        Scope.DISTRICT,
        "district-1",
        True,
    )
    assert _resolve_scope_filter(principal, None, None) == ("district", "district-1")


def test_scope_filter_rejects_cross_scope_for_non_ministry_principal():
    principal = Principal(
        "district-user",
        "auditor",
        Scope.DISTRICT,
        "district-1",
        True,
    )
    with pytest.raises(HTTPException) as exc:
        _resolve_scope_filter(principal, "district", "district-2")
    assert exc.value.status_code == 403


def test_ministry_can_select_a_scope_or_all_scopes():
    principal = Principal(
        "ministry-user",
        "auditor",
        Scope.MINISTRY,
        "ministry",
        True,
    )
    assert _resolve_scope_filter(principal, None, None) == (None, None)
    assert _resolve_scope_filter(principal, "province", "province-7") == (
        "province",
        "province-7",
    )
