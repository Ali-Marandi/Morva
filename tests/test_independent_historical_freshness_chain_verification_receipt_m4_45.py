from __future__ import annotations

import pytest

from morva.api.app import app

from morva.persistence.historical_freshness_chain_verification_receipts_m4_44 import (
    HistoricalFreshnessChainVerificationReceiptRecord,
    HistoricalFreshnessChainVerificationReceiptRepository,
)
from morva.persistence.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    HistoricalSnapshotFreshnessReceiptLineageRepository,
)
from morva.runtime.historical_freshness_chain_verifier_m4_43 import (
    _fingerprint,
    verify_historical_freshness_chain,
)
from morva.runtime.independent_historical_freshness_chain_verification_receipt_verifier_m4_45 import (
    IndependentHistoricalFreshnessChainVerificationReceiptError,
    verify_historical_freshness_chain_verification_receipt,
)
from tests.test_historical_freshness_chain_verifier_m4_43 import _chain_inputs
from tests.test_historical_freshness_chain_verification_receipts_m4_44 import _session_m4_44


def _lineage_id(session, freshness_receipt_id):
    records, _ = HistoricalSnapshotFreshnessReceiptLineageRepository(session).list(
        freshness_receipt_id=freshness_receipt_id,
        limit=1,
    )
    assert len(records) == 1
    return records[0].id


def test_m4_45_independently_verifies_persisted_receipt():
    engine, session = _session_m4_44()
    try:
        inputs = _chain_inputs(session)
        reconstructed = verify_historical_freshness_chain(**inputs)
        record = HistoricalFreshnessChainVerificationReceiptRepository(session).record(
            lineage_id=_lineage_id(session, inputs["freshness_receipt_id"]),
            recorded_by="ministry",
        )

        result = verify_historical_freshness_chain_verification_receipt(
            receipt=record,
            reconstructed=reconstructed,
        )

        assert result.valid is True
        assert result.chain_valid is True
        assert result.blockers == ()
        assert result.persisted_fingerprint == result.reconstructed_fingerprint
        assert len(result.verification_fingerprint) == 64
    finally:
        session.close()
        engine.dispose()


def test_m4_45_blocks_when_persisted_identity_drifts():
    engine, session = _session_m4_44()
    try:
        inputs = _chain_inputs(session)
        reconstructed = verify_historical_freshness_chain(**inputs)
        record = HistoricalFreshnessChainVerificationReceiptRepository(session).record(
            lineage_id=_lineage_id(session, inputs["freshness_receipt_id"]),
            recorded_by="ministry",
        )
        tampered_blockers = ("PERSISTED_DRIFT",)
        record.blockers_json = '["PERSISTED_DRIFT"]'
        record.state = "blocked"
        record.fingerprint = _fingerprint(
            freshness_receipt_id=record.freshness_receipt_id,
            historical_binding_id=record.historical_binding_id,
            snapshot_id=record.snapshot_id,
            lineage_fingerprint=record.lineage_fingerprint,
            freshness_receipt_fingerprint=record.freshness_receipt_fingerprint,
            historical_binding_fingerprint=record.historical_binding_fingerprint,
            snapshot_fingerprint=record.snapshot_fingerprint,
            policy_id=record.policy_id,
            policy_version=record.policy_version,
            policy_fingerprint=record.policy_fingerprint,
            registry_integrity_version=record.registry_integrity_version,
            registry_policy_count=record.registry_policy_count,
            registry_fingerprint=record.registry_fingerprint,
            state=record.state,
            blockers=tampered_blockers,
        )
        session.flush()

        result = verify_historical_freshness_chain_verification_receipt(
            receipt=record,
            reconstructed=reconstructed,
        )

        assert result.valid is False
        assert result.chain_valid is True
        assert result.blockers == ("PERSISTED_RECEIPT_CHAIN_MISMATCH",)
    finally:
        session.close()
        engine.dispose()


def test_m4_45_rejects_structurally_invalid_receipt():
    engine, session = _session_m4_44()
    try:
        inputs = _chain_inputs(session)
        reconstructed = verify_historical_freshness_chain(**inputs)
        record = HistoricalFreshnessChainVerificationReceiptRecord(
            lineage_id=inputs["lineage"].freshness_receipt_id,
            freshness_receipt_id=reconstructed.freshness_receipt_id,
            historical_binding_id=reconstructed.historical_binding_id,
            snapshot_id=reconstructed.snapshot_id,
            lineage_fingerprint=reconstructed.lineage_fingerprint,
            freshness_receipt_fingerprint=reconstructed.freshness_receipt_fingerprint,
            historical_binding_fingerprint=reconstructed.historical_binding_fingerprint,
            snapshot_fingerprint=reconstructed.snapshot_fingerprint,
            policy_id=reconstructed.policy_id,
            policy_version=reconstructed.policy_version,
            policy_fingerprint=reconstructed.policy_fingerprint,
            registry_integrity_version=reconstructed.registry_integrity_version,
            registry_policy_count=reconstructed.registry_policy_count,
            registry_fingerprint=reconstructed.registry_fingerprint,
            state=reconstructed.state,
            blockers_json="[not-json]",
            fingerprint=reconstructed.fingerprint,
            recorded_by="ministry",
        )
        with pytest.raises(
            IndependentHistoricalFreshnessChainVerificationReceiptError,
            match="persisted M4.44 receipt is structurally invalid",
        ):
            verify_historical_freshness_chain_verification_receipt(
                receipt=record,
                reconstructed=reconstructed,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_45_openapi_independent_receipt_verification_route_is_registered():
    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "verification-receipts/{receipt_id}/verify-independent"
    )
    operation = app.openapi()["paths"][path]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/IndependentHistoricalFreshnessChainVerificationReceiptResponse"
    )
