from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.persistence.historical_registry_bound_freshness_receipt_bindings_m4_37 import (
    HistoricalRegistryBoundFreshnessReceiptBindingRepository,
    HistoricalRegistryBoundFreshnessReceiptBindingRecord,
)
from morva.persistence.historical_snapshot_bound_freshness_receipts_m4_40 import (
    HistoricalSnapshotBoundFreshnessReceiptRepository,
    HistoricalSnapshotBoundPolicyReadinessFreshnessRecord,
)
from morva.persistence.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    HistoricalSnapshotFreshnessReceiptLineageRecord,
    HistoricalSnapshotFreshnessReceiptLineageRepository,
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
from morva.runtime.historical_snapshot_bound_policy_readiness_freshness_m4_39 import (
    build_historical_snapshot_bound_policy_readiness_freshness,
)
from morva.runtime.policy_bound_readiness_freshness_m4_29 import (
    build_policy_bound_freshness,
)
from morva.runtime.readiness_convergence_freshness_policy_m4_29 import (
    build_freshness_policy,
)
from morva.runtime.registry_bound_policy_readiness_freshness_m4_34 import (
    build_registry_bound_policy_readiness_freshness,
)


NOW = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)
CANDIDATE_SHA = "a" * 40


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[
            ReadinessConvergenceFreshnessPolicyRecord.__table__,
            RegistryBoundPolicyReadinessFreshnessRecord.__table__,
            FreshnessPolicyRegistrySnapshotRecord.__table__,
            HistoricalRegistryBoundFreshnessReceiptBindingRecord.__table__,
            HistoricalSnapshotBoundPolicyReadinessFreshnessRecord.__table__,
            HistoricalSnapshotFreshnessReceiptLineageRecord.__table__,
        ],
    )
    return engine, Session(engine)


def _source_records(session: Session, *, convergence_fingerprint: str = "b" * 64):
    policy_repository = ReadinessConvergenceFreshnessPolicyRepository(session)
    policy_repository.record(
        build_freshness_policy(
            policy_id="integration-staging-v1",
            policy_version=1,
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
            "fingerprint": convergence_fingerprint,
            "checked_at": checked_at,
            "state": "converged",
        },
    )()
    policy_record = snapshot_repository.resolve_policy(
        snapshot_record.id,
        policy_repository,
        policy_id="integration-staging-v1",
        policy_version=1,
    )
    policy_bound = build_policy_bound_freshness(
        policy_record.to_policy(),
        convergence,
        observed_at=NOW,
    )
    registry_bound = build_registry_bound_policy_readiness_freshness(
        policy_bound,
        registry_integrity_version=snapshot.integrity_version,
        registry_policy_count=snapshot.policy_count,
        registry_fingerprint=snapshot.registry_fingerprint,
    )
    receipt = RegistryBoundPolicyReadinessFreshnessRepository(session).record(
        repository="Ali-Marandi/Morva",
        candidate_sha=CANDIDATE_SHA,
        target_environment="staging",
        organization_scope="school",
        organization_scope_id="school-1",
        freshness=registry_bound,
        recorded_by="ministry",
    )
    historical_binding = (
        HistoricalRegistryBoundFreshnessReceiptBindingRepository(session).bind(
            receipt_id=receipt.id,
            snapshot_id=snapshot_record.id,
            bound_by="ministry",
        )
    )
    historical_freshness = (
        build_historical_snapshot_bound_policy_readiness_freshness(
            policy_bound,
            snapshot_id=snapshot_record.id,
            snapshot_fingerprint=snapshot.fingerprint,
            registry_integrity_version=snapshot.integrity_version,
            registry_policy_count=snapshot.policy_count,
            registry_fingerprint=snapshot.registry_fingerprint,
        )
    )
    freshness_receipt = HistoricalSnapshotBoundFreshnessReceiptRepository(
        session
    ).record(
        repository="Ali-Marandi/Morva",
        candidate_sha=CANDIDATE_SHA,
        target_environment="staging",
        organization_scope="school",
        organization_scope_id="school-1",
        freshness=historical_freshness,
        recorded_by="ministry",
    )
    return snapshot_record, historical_binding, freshness_receipt


def test_m4_41_links_m4_40_receipt_to_m4_37_lineage_and_verifies():
    engine, session = _session()
    try:
        _, binding, freshness_receipt = _source_records(session)
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)

        lineage = repository.bind(
            freshness_receipt_id=freshness_receipt.id,
            historical_binding_id=binding.id,
            bound_by="ministry",
        )
        session.commit()

        verified = repository.verify(lineage.id)
        assert verified.id == lineage.id
        assert verified.to_lineage().fingerprint == lineage.to_lineage().fingerprint
        assert verified.snapshot_id == freshness_receipt.snapshot_id
    finally:
        session.close()
