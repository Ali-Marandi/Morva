from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.persistence.models import Base
from morva.persistence.historical_snapshot_bound_freshness_receipts_m4_40 import (
    HistoricalSnapshotBoundFreshnessReceiptPersistenceError,
    HistoricalSnapshotBoundFreshnessReceiptRepository,
    HistoricalSnapshotBoundPolicyReadinessFreshnessRecord,
)
from morva.persistence.readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyRecord,
    ReadinessConvergenceFreshnessPolicyRepository,
)
from morva.persistence.readiness_freshness_policy_registry_snapshots_m4_36 import (
    FreshnessPolicyRegistrySnapshotRecord,
    FreshnessPolicyRegistrySnapshotRepository,
)
from morva.runtime.historical_snapshot_bound_policy_readiness_freshness_m4_39 import (
    build_historical_snapshot_bound_policy_readiness_freshness,
)
from morva.runtime.policy_bound_readiness_freshness_m4_29 import (
    build_policy_bound_freshness,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    build_freshness_policy,
)


NOW = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)
CANDIDATE_SHA = "a" * 40


def _repositories() -> tuple[object, Session]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[
            ReadinessConvergenceFreshnessPolicyRecord.__table__,
            FreshnessPolicyRegistrySnapshotRecord.__table__,
            HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.__table__,
        ],
    )
    return engine, Session(engine)


def _freshness(
    session: Session,
    *,
    policy_version: int = 1,
):
    policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
    policy_repository.record(
        build_freshness_policy(
            policy_id="integration-staging-v1",
            policy_version=policy_version,
            max_age_seconds=3600,
        ),
        recorded_by="ministry",
    )
    snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
    snapshot_record = snapshot_repository.capture(
        policy_repository,
        captured_by="ministry",
    )
    snapshot = snapshot_record.to_snapshot()
    checked_at = NOW - timedelta(minutes=5)
    convergence = type(
        "Convergence",
        (),
        {
            "fingerprint": "b" * 64,
            "checked_at": checked_at,
            "state": "converged",
        },
    )()
    policy_record = snapshot_repository.resolve_policy(
        snapshot.id,
        policy_repository,
        policy_id="integration-staging-v1",
        policy_version=policy_version,
    )
    policy_bound = build_policy_bound_freshness(
        policy_record.to_policy(),
        convergence,
        observed_at=NOW,
    )
    return build_historical_snapshot_bound_policy_readiness_freshness(
        policy_bound,
        snapshot_id=snapshot.id,
        snapshot_fingerprint=snapshot.fingerprint,
        registry_integrity_version=snapshot.integrity_version,
        registry_policy_count=snapshot.policy_count,
        registry_fingerprint=snapshot.registry_fingerprint,
    )


def test_m4_40_persists_and_reconstructs_historical_snapshot_bound_receipt():
    engine, session = _repositories()
    try:
        freshness = _freshness(session)
        repository = HistoricalSnapshotBoundFreshnessReceiptRepository(session)
        record = repository.record(
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            target_environment="staging",
            organization_scope="school",
            organization_scope_id="school-1",
            freshness=freshness,
            recorded_by="ministry",
        )
        session.commit()

        verified = repository.verify(record.id)
        assert verified.id == record.id
        assert verified.to_freshness().fingerprint == freshness.fingerprint
        assert verified.snapshot_id == freshness.snapshot_id
    finally:
        session.close()
        engine.dispose()


def test_m4_40_same_fingerprint_is_idempotent_only_for_same_actor():
    engine, session = _repositories()
    try:
        freshness = _freshness(session)
        repository = HistoricalSnapshotBoundFreshnessReceiptRepository(session)
        first = repository.record(
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            target_environment="staging",
            organization_scope="school",
            organization_scope_id="school-1",
            freshness=freshness,
            recorded_by="ministry",
        )
        second = repository.record(
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            target_environment="staging",
            organization_scope="school",
            organization_scope_id="school-1",
            freshness=freshness,
            recorded_by="ministry",
        )
        assert second.id == first.id
        with pytest.raises(HistoricalSnapshotBoundFreshnessReceiptPersistenceError):
            repository.record(
                repository="Ali-Marandi/Morva",
                candidate_sha=CANDIDATE_SHA,
                target_environment="staging",
                organization_scope="school",
                organization_scope_id="school-1",
                freshness=freshness,
                recorded_by="other-ministry",
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_40_verification_rejects_tampered_snapshot_identity():
    engine, session = _repositories()
    try:
        freshness = _freshness(session)
        repository = HistoricalSnapshotBoundFreshnessReceiptRepository(session)
        record = repository.record(
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            target_environment="staging",
            organization_scope="school",
            organization_scope_id="school-1",
            freshness=freshness,
            recorded_by="ministry",
        )
        record.snapshot_fingerprint = "d" * 64
        session.flush()
        with pytest.raises(
            HistoricalSnapshotBoundFreshnessReceiptPersistenceError,
            match="structurally invalid|snapshot fingerprint",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_40_history_supports_scope_and_cursor_filtering():
    engine, session = _repositories()
    try:
        freshness = _freshness(session)
        repository = HistoricalSnapshotBoundFreshnessReceiptRepository(session)
        first = repository.record(
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            target_environment="staging",
            organization_scope="school",
            organization_scope_id="school-1",
            freshness=freshness,
            recorded_by="ministry",
        )
        page, has_more = repository.list(
            organization_scope="school",
            organization_scope_id="school-1",
            limit=1,
        )
        assert page[0].id == first.id
        assert has_more is False
    finally:
        session.close()
        engine.dispose()


def test_m4_40_openapi_contract_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    assert (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipts"
    ) in paths
    assert (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipts/{receipt_id}/verify"
    ) in paths
