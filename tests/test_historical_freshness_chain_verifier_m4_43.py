from __future__ import annotations

from uuid import uuid4

from morva.persistence.historical_registry_bound_freshness_receipt_bindings_m4_37 import (
    HistoricalRegistryBoundFreshnessReceiptBindingRepository,
)
from morva.persistence.historical_snapshot_bound_freshness_receipts_m4_40 import (
    HistoricalSnapshotBoundFreshnessReceiptRepository,
)
from morva.persistence.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    HistoricalSnapshotFreshnessReceiptLineageRepository,
)
from morva.runtime.historical_freshness_chain_verifier_m4_43 import (
    HistoricalFreshnessChainVerification,
    verify_historical_freshness_chain,
)
from morva.runtime.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    build_historical_snapshot_freshness_receipt_lineage,
)

from tests.test_historical_snapshot_freshness_receipt_lineage_m4_41 import (
    _session,
    _source_records,
)


def _chain_inputs(session, *, convergence_fingerprint: str = "b" * 64):
    snapshot_record, binding_record, receipt_record = _source_records(
        session,
        convergence_fingerprint=convergence_fingerprint,
    )
    lineage_record = HistoricalSnapshotFreshnessReceiptLineageRepository(session).bind(
        freshness_receipt_id=receipt_record.id,
        historical_binding_id=binding_record.id,
        bound_by="ministry",
    )
    freshness = HistoricalSnapshotBoundFreshnessReceiptRepository(session).verify(
        receipt_record.id
    ).to_freshness()
    historical_binding = (
        HistoricalRegistryBoundFreshnessReceiptBindingRepository(session)
        .verify(binding_record.id)
        .to_binding()
    )
    snapshot = snapshot_record.to_snapshot()
    lineage = lineage_record.to_lineage()
    return {
        "freshness_receipt_id": receipt_record.id,
        "freshness": freshness,
        "historical_binding_id": binding_record.id,
        "historical_binding": historical_binding,
        "snapshot_id": snapshot_record.id,
        "snapshot": snapshot,
        "lineage": lineage,
    }


def test_m4_43_verifies_the_complete_historical_freshness_chain():
    engine, session = _session()
    try:
        inputs = _chain_inputs(session)
        result = verify_historical_freshness_chain(**inputs)

        assert isinstance(result, HistoricalFreshnessChainVerification)
        assert result.valid is True
        assert result.state == "verified"
        assert result.blockers == ()
        assert len(result.fingerprint) == 64
    finally:
        session.close()
        engine.dispose()


def test_m4_43_is_deterministic_for_identical_chain_inputs():
    engine, session = _session()
    try:
        inputs = _chain_inputs(session)
        first = verify_historical_freshness_chain(**inputs)
        second = verify_historical_freshness_chain(**inputs)

        assert first.fingerprint == second.fingerprint
        assert first.to_payload() == second.to_payload()
    finally:
        session.close()
        engine.dispose()


def test_m4_43_blocks_when_lineage_snapshot_identity_drifts():
    engine, session = _session()
    try:
        inputs = _chain_inputs(session)
        original = inputs["lineage"]
        tampered_lineage = build_historical_snapshot_freshness_receipt_lineage(
            freshness_receipt_id=original.freshness_receipt_id,
            historical_binding_id=original.historical_binding_id,
            snapshot_id=uuid4(),
            freshness_receipt_fingerprint=original.freshness_receipt_fingerprint,
            historical_binding_fingerprint=original.historical_binding_fingerprint,
            snapshot_fingerprint=original.snapshot_fingerprint,
            registry_integrity_version=original.registry_integrity_version,
            registry_policy_count=original.registry_policy_count,
            registry_fingerprint=original.registry_fingerprint,
            policy_id=original.policy_id,
            policy_version=original.policy_version,
            policy_fingerprint=original.policy_fingerprint,
        )

        result = verify_historical_freshness_chain(
            **{**inputs, "lineage": tampered_lineage}
        )

        assert result.valid is False
        assert result.state == "blocked"
        assert "SNAPSHOT_ID_MISMATCH" in result.blockers
    finally:
        session.close()
        engine.dispose()


def test_m4_43_blocks_when_registry_identity_drifts():
    engine, session = _session()
    try:
        inputs = _chain_inputs(session)
        original = inputs["lineage"]
        tampered_lineage = build_historical_snapshot_freshness_receipt_lineage(
            freshness_receipt_id=original.freshness_receipt_id,
            historical_binding_id=original.historical_binding_id,
            snapshot_id=original.snapshot_id,
            freshness_receipt_fingerprint=original.freshness_receipt_fingerprint,
            historical_binding_fingerprint=original.historical_binding_fingerprint,
            snapshot_fingerprint=original.snapshot_fingerprint,
            registry_integrity_version=original.registry_integrity_version,
            registry_policy_count=original.registry_policy_count,
            registry_fingerprint="d" * 64,
            policy_id=original.policy_id,
            policy_version=original.policy_version,
            policy_fingerprint=original.policy_fingerprint,
        )

        result = verify_historical_freshness_chain(
            **{**inputs, "lineage": tampered_lineage}
        )

        assert result.valid is False
        assert "LINEAGE_REGISTRY_FINGERPRINT_MISMATCH" in result.blockers
    finally:
        session.close()
        engine.dispose()


def test_m4_43_payload_is_explicitly_evidence_only():
    engine, session = _session()
    try:
        inputs = _chain_inputs(session)
        result = verify_historical_freshness_chain(**inputs)
        payload = result.to_payload()

        assert payload["valid"] is True
        assert payload["state"] == "verified"
        assert payload["policy"]["policy_id"] == "integration-staging-v1"
        assert payload["registry"]["policy_count"] == 1
    finally:
        session.close()
        engine.dispose()