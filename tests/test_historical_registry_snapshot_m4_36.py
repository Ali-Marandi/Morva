from __future__ import annotations

from sqlalchemy import create_engine

from morva.persistence.models import Base
from morva.persistence.readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyRecord,
    ReadinessConvergenceFreshnessPolicyRepository,
)
from morva.persistence.readiness_freshness_policy_registry_snapshots_m4_36 import (
    FreshnessPolicyRegistrySnapshotRecord,
    FreshnessPolicyRegistrySnapshotPersistenceError,
    FreshnessPolicyRegistrySnapshotRepository,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    build_freshness_policy,
)
from morva.runtime.readiness_freshness_policy_registry_snapshot_m4_36 import (
    FreshnessPolicyRegistrySnapshotError,
    build_freshness_policy_registry_snapshot,
)


def _repositories():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[
            ReadinessConvergenceFreshnessPolicyRecord.__table__,
            FreshnessPolicyRegistrySnapshotRecord.__table__,
        ],
    )
    from sqlalchemy.orm import Session

    return engine, Session(engine)


def test_m4_36_snapshot_is_deterministic_and_canonical():
    engine, session = _repositories()
    try:
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        first = policy_repository.record(
            build_freshness_policy(
                policy_id="z-policy",
                policy_version=1,
                max_age_seconds=3600,
            ),
            recorded_by="auditor",
        )
        second = policy_repository.record(
            build_freshness_policy(
                policy_id="a-policy",
                policy_version=1,
                max_age_seconds=1800,
            ),
            recorded_by="auditor",
        )

        count, registry_fingerprint, member_ids = (
            policy_repository.integrity_snapshot_manifest()
        )
        snapshot_one = build_freshness_policy_registry_snapshot(
            integrity_version=1,
            policy_count=count,
            registry_fingerprint=registry_fingerprint,
            member_record_ids=member_ids,
        )
        snapshot_two = build_freshness_policy_registry_snapshot(
            integrity_version=1,
            policy_count=count,
            registry_fingerprint=registry_fingerprint,
            member_record_ids=tuple(reversed(member_ids)),
        )

        assert count == 2
        assert set(snapshot_one.member_record_ids) == {first.id, second.id}
        assert snapshot_one.fingerprint == snapshot_two.fingerprint
        assert snapshot_one.membership_fingerprint == snapshot_two.membership_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_36_snapshot_round_trip_and_reconstruction():
    engine, session = _repositories()
    try:
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        policy_repository.record(
            build_freshness_policy(
                policy_id="integration-staging",
                policy_version=1,
                max_age_seconds=3600,
            ),
            recorded_by="auditor",
        )
        repository = FreshnessPolicyRegistrySnapshotRepository(session)
        first = repository.capture(policy_repository, captured_by="auditor")
        session.commit()

        rebuilt = repository.reconstruct(first.id, policy_repository)
        assert rebuilt.to_snapshot().fingerprint == first.to_snapshot().fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_36_later_registry_append_does_not_change_historical_snapshot():
    engine, session = _repositories()
    try:
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        policy_repository.record(
            build_freshness_policy(
                policy_id="integration-staging",
                policy_version=1,
                max_age_seconds=3600,
            ),
            recorded_by="auditor",
        )
        repository = FreshnessPolicyRegistrySnapshotRepository(session)
        snapshot = repository.capture(policy_repository, captured_by="auditor")
        historical = snapshot.to_snapshot()
        policy_repository.record(
            build_freshness_policy(
                policy_id="integration-staging",
                policy_version=2,
                max_age_seconds=1800,
            ),
            recorded_by="auditor",
        )
        session.commit()

        rebuilt = repository.reconstruct(snapshot.id, policy_repository)
        assert rebuilt.to_snapshot().fingerprint == historical.fingerprint
        assert rebuilt.to_snapshot().policy_count == 1
    finally:
        session.close()
        engine.dispose()


def test_m4_36_reconstruction_fails_on_member_mutation():
    engine, session = _repositories()
    try:
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        record = policy_repository.record(
            build_freshness_policy(
                policy_id="integration-staging",
                policy_version=1,
                max_age_seconds=3600,
            ),
            recorded_by="auditor",
        )
        repository = FreshnessPolicyRegistrySnapshotRepository(session)
        snapshot = repository.capture(policy_repository, captured_by="auditor")
        record.max_age_seconds = 7200
        session.commit()

        try:
            repository.reconstruct(snapshot.id, policy_repository)
        except FreshnessPolicyRegistrySnapshotPersistenceError as exc:
            assert "structurally invalid" in str(exc)
        else:
            raise AssertionError("mutated snapshot member must fail closed")
    finally:
        session.close()
        engine.dispose()


def test_m4_36_reconstruction_fails_when_member_is_missing():
    engine, session = _repositories()
    try:
        policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
        policy_repository.record(
            build_freshness_policy(
                policy_id="integration-staging",
                policy_version=1,
                max_age_seconds=3600,
            ),
            recorded_by="auditor",
        )
        repository = FreshnessPolicyRegistrySnapshotRepository(session)
        snapshot = repository.capture(policy_repository, captured_by="auditor")
        session.commit()
        session.delete(
            session.get(
                ReadinessConvergenceFreshnessPolicyRecord,
                snapshot.to_snapshot().member_record_ids[0],
            )
        )
        session.commit()

        try:
            repository.reconstruct(snapshot.id, policy_repository)
        except FreshnessPolicyRegistrySnapshotPersistenceError as exc:
            assert "missing" in str(exc)
        else:
            raise AssertionError("missing snapshot member must fail closed")
    finally:
        session.close()
        engine.dispose()


def test_m4_36_rejects_duplicate_or_noncanonical_members():
    import uuid

    member = uuid.uuid4()
    try:
        build_freshness_policy_registry_snapshot(
            integrity_version=1,
            policy_count=2,
            registry_fingerprint="a" * 64,
            member_record_ids=(member, member),
        )
    except FreshnessPolicyRegistrySnapshotError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("duplicate member ids must be rejected")
