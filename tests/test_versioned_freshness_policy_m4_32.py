from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.models import Base
from morva.persistence.readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyRecord,
    ReadinessConvergenceFreshnessPolicyRepository,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    build_freshness_policy,
)


def test_policy_version_changes_identity_fingerprint():
    version_one = build_freshness_policy(
        policy_id="integration-staging",
        policy_version=1,
        max_age_seconds=3600,
    )
    version_two = build_freshness_policy(
        policy_id="integration-staging",
        policy_version=2,
        max_age_seconds=3600,
    )

    assert version_one.fingerprint != version_two.fingerprint
    assert version_two.policy_version == 2


def test_policy_version_two_round_trips_through_registry():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[ReadinessConvergenceFreshnessPolicyRecord.__table__],
    )
    local = sessionmaker(bind=engine, future=True)

    with local() as session:
        repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        policy = build_freshness_policy(
            policy_id="integration-staging",
            policy_version=2,
            max_age_seconds=1800,
        )
        record = repository.record(policy, recorded_by="ministry-auditor")
        restored = repository.get(
            policy_id=policy.policy_id,
            policy_version=2,
        )

        assert record.policy_version == 2
        assert restored is not None
        assert restored.to_policy().fingerprint == policy.fingerprint


def test_policy_versions_are_append_only_for_same_policy_id():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[ReadinessConvergenceFreshnessPolicyRecord.__table__],
    )
    local = sessionmaker(bind=engine, future=True)

    with local() as session:
        repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        first = repository.record(
            build_freshness_policy(
                policy_id="integration-staging",
                policy_version=1,
                max_age_seconds=3600,
            ),
            recorded_by="ministry-auditor",
        )
        second = repository.record(
            build_freshness_policy(
                policy_id="integration-staging",
                policy_version=2,
                max_age_seconds=1800,
            ),
            recorded_by="ministry-auditor",
        )

        assert first.policy_version == 1
        assert second.policy_version == 2
        assert first.id != second.id
        assert first.fingerprint != second.fingerprint


def test_policy_version_must_be_positive():
    from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
        ReadinessConvergenceFreshnessPolicyError,
    )

    try:
        build_freshness_policy(
            policy_id="integration-staging",
            policy_version=0,
            max_age_seconds=3600,
        )
    except ReadinessConvergenceFreshnessPolicyError as exc:
        assert "policy_version must be positive" in str(exc)
    else:
        raise AssertionError("non-positive policy version must be rejected")


def test_registry_integrity_snapshot_is_deterministic_and_changes_with_append():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[ReadinessConvergenceFreshnessPolicyRecord.__table__],
    )
    local = sessionmaker(bind=engine, future=True)

    with local() as session:
        repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        first = repository.record(
        build_freshness_policy(
            policy_id="integration-staging",
            policy_version=1,
            max_age_seconds=3600,
        ),
        recorded_by="auditor-1",
    )
    count_one, fingerprint_one = repository.integrity_snapshot()
    count_two, fingerprint_two = repository.integrity_snapshot()

    assert first.policy_version == 1
    assert count_one == count_two == 1
    assert fingerprint_one == fingerprint_two

    repository.record(
        build_freshness_policy(
            policy_id="integration-staging",
            policy_version=2,
            max_age_seconds=1800,
        ),
        recorded_by="auditor-1",
    )
    count_three, fingerprint_three = repository.integrity_snapshot()

        assert count_three == 2
        assert fingerprint_three != fingerprint_one
