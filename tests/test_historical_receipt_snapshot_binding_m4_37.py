from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.persistence.historical_registry_bound_freshness_receipt_bindings_m4_37 import (
    HistoricalRegistryBoundFreshnessReceiptBindingRecord,
    HistoricalRegistryBoundFreshnessReceiptBindingRepository,
    HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError,
)
from morva.persistence.models import Base
from morva.persistence.readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyRecord,
    ReadinessConvergenceFreshnessPolicyRepository,
)
from morva.persistence.readiness_freshness_policy_registry_snapshots_m4_36 import (
    FreshnessPolicyRegistrySnapshotRecord,
    FreshnessPolicyRegistrySnapshotRepository,
)
from morva.persistence.registry_bound_policy_readiness_freshness_records_m4_35 import (
    RegistryBoundPolicyReadinessFreshnessRecord,
    RegistryBoundPolicyReadinessFreshnessRepository,
)
from morva.runtime.policy_bound_readiness_freshness_m4_29 import (
    build_policy_bound_freshness,
)
from morva.runtime.readiness_convergence_freshness_m4_28 import (
    ReadinessConvergenceFreshnessAssessment,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    build_freshness_policy,
)
from morva.runtime.registry_bound_policy_readiness_freshness_m4_34 import (
    build_registry_bound_policy_readiness_freshness,
)


NOW = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


def _assessment(observed_at: datetime, convergence_fingerprint: str):
    policy = build_freshness_policy(
        policy_id="integration-staging-v1",
        policy_version=1,
        max_age_seconds=3600,
    )
    checked_at = NOW - timedelta(minutes=5)
    age_seconds = max(int((observed_at - checked_at).total_seconds()), 0)
    payload = {
        "freshness_version": 1,
        "convergence_fingerprint": convergence_fingerprint,
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
        "max_age_seconds": policy.max_age_seconds,
        "age_seconds": age_seconds,
        "state": "fresh",
        "blockers": [],
    }
    import hashlib
    import json

    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ReadinessConvergenceFreshnessAssessment(
        freshness_version=1,
        convergence_fingerprint=convergence_fingerprint,
        checked_at=checked_at,
        observed_at=observed_at,
        max_age_seconds=policy.max_age_seconds,
        age_seconds=age_seconds,
        state="fresh",
        blockers=(),
        fingerprint=fingerprint,
    ), policy


def _repositories():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[
            ReadinessConvergenceFreshnessPolicyRecord.__table__,
            FreshnessPolicyRegistrySnapshotRecord.__table__,
            RegistryBoundPolicyReadinessFreshnessRecord.__table__,
            HistoricalRegistryBoundFreshnessReceiptBindingRecord.__table__,
        ],
    )
    return engine, Session(engine)


def _receipt(session: Session, *, policy_id: str = "integration-staging-v1"):
    policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
    policy = policy_repository.record(
        build_freshness_policy(
            policy_id=policy_id,
            policy_version=1,
            max_age_seconds=3600,
        ),
        recorded_by="auditor",
    )
    assessment, policy_runtime = _assessment(NOW, "a" * 64)
    policy_bound = build_policy_bound_freshness(
        policy_runtime,
        type(
            "Convergence",
            (),
            {
                "fingerprint": "a" * 64,
                "checked_at": assessment.checked_at,
                "state": "converged",
            },
        )(),
        observed_at=NOW,
    )
    registry_count, registry_fingerprint = policy_repository.integrity_snapshot()
    freshness = build_registry_bound_policy_readiness_freshness(
        policy_bound,
        registry_integrity_version=1,
        registry_policy_count=registry_count,
        registry_fingerprint=registry_fingerprint,
    )
    receipt_repository = RegistryBoundPolicyReadinessFreshnessRepository(session)
    receipt = receipt_repository.record(
        repository="Ali-Marandi/Morva",
        candidate_sha="c" * 40,
        target_environment="staging",
        organization_scope="district",
        organization_scope_id="district-1",
        freshness=freshness,
        recorded_by="auditor",
    )
    return policy, receipt


def test_m4_37_binds_receipt_to_exact_historical_snapshot_and_is_idempotent():
    engine, session = _repositories()
    try:
        policy, receipt = _receipt(session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
        snapshot = snapshot_repository.capture(policy_repository, captured_by="auditor")
        binding_repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(session)
        first = binding_repository.bind(
            receipt_id=receipt.id,
            snapshot_id=snapshot.id,
            bound_by="auditor",
        )
        second = binding_repository.bind(
            receipt_id=receipt.id,
            snapshot_id=snapshot.id,
            bound_by="auditor",
        )
        session.commit()

        assert first.id == second.id
        assert first.to_binding().receipt_id == receipt.id
        assert first.to_binding().snapshot_id == snapshot.id
        assert first.to_binding().policy_fingerprint == policy.fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_37_historical_binding_survives_later_registry_append_and_reverifies():
    engine, session = _repositories()
    try:
        _, receipt = _receipt(session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
        snapshot = snapshot_repository.capture(policy_repository, captured_by="auditor")
        binding_repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(session)
        binding = binding_repository.bind(
            receipt_id=receipt.id,
            snapshot_id=snapshot.id,
            bound_by="auditor",
        )
        policy_repository.record(
            build_freshness_policy(
                policy_id="integration-staging-v1",
                policy_version=2,
                max_age_seconds=1800,
            ),
            recorded_by="auditor",
        )
        session.commit()

        verified = binding_repository.verify(binding.id)
        assert verified.id == binding.id
    finally:
        session.close()
        engine.dispose()


def test_m4_37_rejects_receipt_snapshot_registry_mismatch():
    engine, session = _repositories()
    try:
        _, receipt = _receipt(session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
        snapshot = snapshot_repository.capture(policy_repository, captured_by="auditor")
        receipt.registry_fingerprint = "d" * 64
        try:
            HistoricalRegistryBoundFreshnessReceiptBindingRepository(session).bind(
                receipt_id=receipt.id,
                snapshot_id=snapshot.id,
                bound_by="auditor",
            )
        except HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError as exc:
            assert "structurally invalid" in str(exc)
        else:
            raise AssertionError("tampered receipt must fail closed")
    finally:
        session.close()
        engine.dispose()


def test_m4_37_verification_rejects_tampered_bound_policy_identity():
    engine, session = _repositories()
    try:
        _, receipt = _receipt(session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        snapshot = FreshnessPolicyRegistrySnapshotRepository(session).capture(
            policy_repository,
            captured_by="auditor",
        )
        repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(session)
        binding = repository.bind(
            receipt_id=receipt.id,
            snapshot_id=snapshot.id,
            bound_by="auditor",
        )
        binding.policy_id = "tampered-policy"
        try:
            repository.verify(binding.id)
        except HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError as exc:
            assert "bound policy id differs" in str(exc)
        else:
            raise AssertionError("tampered bound policy identity must fail closed")
    finally:
        session.close()
        engine.dispose()


def test_m4_37_rejects_binding_from_different_actor():
    engine, session = _repositories()
    try:
        _, receipt = _receipt(session)
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        snapshot = FreshnessPolicyRegistrySnapshotRepository(session).capture(
            policy_repository,
            captured_by="auditor",
        )
        repository = HistoricalRegistryBoundFreshnessReceiptBindingRepository(session)
        repository.bind(
            receipt_id=receipt.id,
            snapshot_id=snapshot.id,
            bound_by="first-actor",
        )
        try:
            repository.bind(
                receipt_id=receipt.id,
                snapshot_id=snapshot.id,
                bound_by="second-actor",
            )
        except HistoricalRegistryBoundFreshnessReceiptBindingPersistenceError as exc:
            assert "different actor" in str(exc)
        else:
            raise AssertionError("actor mismatch must fail closed")
    finally:
        session.close()
        engine.dispose()


def test_m4_37_openapi_contracts_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    create_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-bound-integrity/receipt-snapshot-bindings"
    )
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-bound-integrity/receipt-snapshot-bindings/{binding_id}/verify"
    )
    assert create_path in paths
    assert verify_path in paths
    assert paths[create_path]["post"]["responses"]["200"]
    assert paths[verify_path]["get"]["responses"]["200"]
