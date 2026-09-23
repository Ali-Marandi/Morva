from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.models import Base
from morva.persistence.readiness_convergence_freshness_policy_records_m4_30 import (
    ReadinessConvergenceFreshnessPolicyPersistenceError,
    ReadinessConvergenceFreshnessPolicyRecord,
    ReadinessConvergenceFreshnessPolicyRepository,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    build_freshness_policy,
)


NOW = datetime(2026, 9, 23, 19, tzinfo=timezone.utc)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[ReadinessConvergenceFreshnessPolicyRecord.__table__],
    )
    local = sessionmaker(bind=engine, future=True)
    with local() as db:
        yield db
        db.rollback()


def test_policy_round_trip_is_deterministic(session):
    repository = ReadinessConvergenceFreshnessPolicyRepository(session)
    policy = build_freshness_policy(
        policy_id="integration-staging-v1",
        max_age_seconds=3600,
    )

    record = repository.record(policy, recorded_by="ministry-auditor")
    restored = repository.get(policy_id=policy.policy_id)

    assert restored is not None
    assert restored.to_policy().fingerprint == policy.fingerprint
    assert record.recorded_by == "ministry-auditor"


def test_policy_record_is_idempotent_for_same_actor(session):
    repository = ReadinessConvergenceFreshnessPolicyRepository(session)
    policy = build_freshness_policy(
        policy_id="integration-staging-v1",
        max_age_seconds=3600,
    )

    first = repository.record(policy, recorded_by="auditor-1")
    second = repository.record(policy, recorded_by="auditor-1")

    assert first.id == second.id


def test_same_policy_cannot_be_recorded_by_different_actor(session):
    repository = ReadinessConvergenceFreshnessPolicyRepository(session)
    policy = build_freshness_policy(
        policy_id="integration-staging-v1",
        max_age_seconds=3600,
    )
    repository.record(policy, recorded_by="auditor-1")

    with pytest.raises(
        ReadinessConvergenceFreshnessPolicyPersistenceError,
        match="different actor",
    ):
        repository.record(policy, recorded_by="auditor-2")


def test_same_id_and_version_cannot_change_policy(session):
    repository = ReadinessConvergenceFreshnessPolicyRepository(session)
    first = build_freshness_policy(
        policy_id="integration-staging-v1",
        max_age_seconds=3600,
    )
    repository.record(first, recorded_by="auditor-1")

    second = build_freshness_policy(
        policy_id="integration-staging-v1",
        max_age_seconds=7200,
    )

    with pytest.raises(
        ReadinessConvergenceFreshnessPolicyPersistenceError,
    ):
        repository.record(second, recorded_by="auditor-1")


def test_tampered_persisted_policy_fails_closed(session):
    repository = ReadinessConvergenceFreshnessPolicyRepository(session)
    record = repository.record(
        build_freshness_policy(
            policy_id="integration-staging-v1",
            max_age_seconds=3600,
        ),
        recorded_by="auditor-1",
    )
    record.max_age_seconds = 7200

    with pytest.raises(
        ReadinessConvergenceFreshnessPolicyPersistenceError,
        match="structurally invalid",
    ):
        record.to_policy()


def test_get_rejects_invalid_version(session):
    repository = ReadinessConvergenceFreshnessPolicyRepository(session)

    with pytest.raises(
        ReadinessConvergenceFreshnessPolicyPersistenceError,
        match="policy_version must be positive",
    ):
        repository.get(
            policy_id="integration-staging-v1",
            policy_version=0,
        )


def test_policy_history_is_cursor_paginated_and_descending(session):
    repository = ReadinessConvergenceFreshnessPolicyRepository(session)
    first = repository.record(
        build_freshness_policy(
            policy_id="policy-a",
            max_age_seconds=3600,
        ),
        recorded_by="auditor-1",
    )
    second = repository.record(
        build_freshness_policy(
            policy_id="policy-b",
            max_age_seconds=7200,
        ),
        recorded_by="auditor-1",
    )

    first_page, has_more = repository.list(limit=1)
    assert has_more is True
    assert [record.id for record in first_page] == [second.id]

    second_page, second_has_more = repository.list(
        before_created_at=second.created_at,
        before_id=second.id,
        limit=1,
    )
    assert second_has_more is False
    assert [record.id for record in second_page] == [first.id]


def test_policy_history_rejects_invalid_limit(session):
    repository = ReadinessConvergenceFreshnessPolicyRepository(session)

    with pytest.raises(
        ReadinessConvergenceFreshnessPolicyPersistenceError,
        match="limit must be between 1 and 100",
    ):
        repository.list(limit=0)
