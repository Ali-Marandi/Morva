from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.persistence.models import Base
from morva.persistence.readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyRecord,
    ReadinessConvergenceFreshnessPolicyRepository,
)
from morva.persistence.readiness_freshness_policy_registry_snapshots_m4_36 import (
    FreshnessPolicyRegistrySnapshotRecord,
    FreshnessPolicyRegistrySnapshotRepository,
    FreshnessPolicyRegistrySnapshotPersistenceError,
)
from morva.persistence.scope_bound_readiness_convergence_records_m4_27 import (
    ScopeBoundReadinessConvergenceRecord,
)
from morva.runtime.historical_snapshot_bound_policy_readiness_freshness_m4_39 import (
    HistoricalSnapshotBoundPolicyReadinessFreshnessError,
    build_historical_snapshot_bound_policy_readiness_freshness,
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


NOW = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


def _repositories():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[
            ReadinessConvergenceFreshnessPolicyRecord.__table__,
            FreshnessPolicyRegistrySnapshotRecord.__table__,
        ],
    )
    return engine, Session(engine)


def _policy_bound():
    policy = build_freshness_policy(
        policy_id="integration-staging-v1",
        policy_version=1,
        max_age_seconds=3600,
    )
    checked_at = NOW - timedelta(minutes=5)
    observed_at = NOW
    payload = {
        "freshness_version": 1,
        "convergence_fingerprint": "a" * 64,
        "checked_at": checked_at.isoformat(),
        "observed_at": observed_at.isoformat(),
        "max_age_seconds": policy.max_age_seconds,
        "age_seconds": 300,
        "state": "fresh",
        "blockers": [],
    }
    import hashlib
    import json

    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assessment = ReadinessConvergenceFreshnessAssessment(
        freshness_version=1,
        convergence_fingerprint="a" * 64,
        checked_at=checked_at,
        observed_at=observed_at,
        max_age_seconds=3600,
        age_seconds=300,
        state="fresh",
        blockers=(),
        fingerprint=fingerprint,
    )
    return build_policy_bound_freshness(
        policy,
        type(
            "Convergence",
            (),
            {
                "fingerprint": "a" * 64,
                "checked_at": checked_at,
                "state": "converged",
            },
        )(),
        observed_at=observed_at,
    )


def test_m4_39_snapshot_bound_fingerprint_is_deterministic():
    snapshot_id = __import__("uuid").uuid4()
    policy_bound = _policy_bound()
    first = build_historical_snapshot_bound_policy_readiness_freshness(
        policy_bound,
        snapshot_id=snapshot_id,
        snapshot_fingerprint="b" * 64,
        registry_integrity_version=1,
        registry_policy_count=1,
        registry_fingerprint="c" * 64,
    )
    second = build_historical_snapshot_bound_policy_readiness_freshness(
        policy_bound,
        snapshot_id=snapshot_id,
        snapshot_fingerprint="b" * 64,
        registry_integrity_version=1,
        registry_policy_count=1,
        registry_fingerprint="c" * 64,
    )
    assert first.fingerprint == second.fingerprint
    assert first.to_payload()["snapshot"]["id"] == str(snapshot_id)


def test_m4_39_historical_snapshot_resolution_rejects_later_policy():
    engine, session = _repositories()
    try:
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        policy_repository.record(
            build_freshness_policy(
                policy_id="integration-staging-v1",
                policy_version=1,
                max_age_seconds=3600,
            ),
            recorded_by="auditor",
        )
        snapshot_repository = FreshnessPolicyRegistrySnapshotRepository(session)
        snapshot = snapshot_repository.capture(
            policy_repository,
            captured_by="auditor",
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
        try:
            snapshot_repository.resolve_policy(
                snapshot.id,
                policy_repository,
                policy_id="integration-staging-v1",
                policy_version=2,
            )
        except FreshnessPolicyRegistrySnapshotPersistenceError as exc:
            assert "not a member" in str(exc)
        else:
            raise AssertionError("later policy must not resolve from historical snapshot")
    finally:
        session.close()
        engine.dispose()


def test_m4_39_runtime_rejects_tampered_snapshot_fingerprint():
    policy_bound = _policy_bound()
    snapshot_id = __import__("uuid").uuid4()
    result = build_historical_snapshot_bound_policy_readiness_freshness(
        policy_bound,
        snapshot_id=snapshot_id,
        snapshot_fingerprint="b" * 64,
        registry_integrity_version=1,
        registry_policy_count=1,
        registry_fingerprint="c" * 64,
    )
    try:
        type(result)(
            binding_version=result.binding_version,
            snapshot_id=result.snapshot_id,
            snapshot_fingerprint="d" * 64,
            registry_integrity_version=result.registry_integrity_version,
            registry_policy_count=result.registry_policy_count,
            registry_fingerprint=result.registry_fingerprint,
            policy_bound=result.policy_bound,
            fingerprint=result.fingerprint,
        )
    except HistoricalSnapshotBoundPolicyReadinessFreshnessError as exc:
        assert "fingerprint mismatch" in str(exc)
    else:
        raise AssertionError("tampered snapshot identity must fail closed")
