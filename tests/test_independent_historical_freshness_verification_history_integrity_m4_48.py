from __future__ import annotations

from datetime import timezone

from morva.persistence.historical_freshness_chain_verification_receipts_m4_44 import (
    HistoricalFreshnessChainVerificationReceiptRepository,
)
from morva.persistence.historical_freshness_verification_history_integrity_m4_47 import (
    HistoricalFreshnessVerificationHistoryIntegrityRecord,
    HistoricalFreshnessVerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_freshness_receipt_verifications_m4_46 import (
    IndependentHistoricalFreshnessReceiptVerificationRepository,
)
from morva.runtime.independent_historical_freshness_verification_history_integrity_verifier_m4_48 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrityError,
    independently_verify_historical_freshness_verification_history_integrity,
)
from tests.test_historical_freshness_chain_verifier_m4_43 import _chain_inputs
from tests.test_historical_freshness_chain_verification_receipts_m4_44 import _session_m4_44
from tests.test_independent_historical_freshness_chain_verification_receipt_m4_45 import (
    _lineage_id,
)


def _session_m4_48():
    engine, session = _session_m4_44()
    source_record = __import__(
        "morva.persistence.independent_historical_freshness_receipt_verifications_m4_46",
        fromlist=["IndependentHistoricalFreshnessReceiptVerificationRecord"],
    ).IndependentHistoricalFreshnessReceiptVerificationRecord
    source_record.__table__.create(bind=engine, checkfirst=True)
    HistoricalFreshnessVerificationHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_source_verification(session, convergence_fingerprint: str = "a" * 64):
    inputs = _chain_inputs(session, convergence_fingerprint=convergence_fingerprint)
    source = HistoricalFreshnessChainVerificationReceiptRepository(session).record(
        lineage_id=_lineage_id(session, inputs["freshness_receipt_id"]),
        recorded_by="ministry",
    )
    return IndependentHistoricalFreshnessReceiptVerificationRepository(session).record(
        receipt_id=source.id,
        recorded_by="ministry",
    )


def test_m4_48_independently_verifies_snapshot():
    engine, session = _session_m4_48()
    try:
        _persist_source_verification(session)
        snapshot = HistoricalFreshnessVerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        source_records = (
            IndependentHistoricalFreshnessReceiptVerificationRepository(session)
            .list(limit=100)[0]
        )
        result = independently_verify_historical_freshness_verification_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        assert result.valid is True
        assert result.blockers == ()
        assert result.persisted_fingerprint == result.reconstructed_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_48_preserves_point_in_time_boundary():
    engine, session = _session_m4_48()
    try:
        _persist_source_verification(session, "a" * 64)
        snapshot = HistoricalFreshnessVerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        _persist_source_verification(session, "b" * 64)
        all_records = (
            IndependentHistoricalFreshnessReceiptVerificationRepository(session)
            .list(limit=100)[0]
        )
        snapshot_created_at = snapshot.created_at
        if snapshot_created_at.tzinfo is None:
            snapshot_created_at = snapshot_created_at.replace(tzinfo=timezone.utc)
        source_records = []
        for record in all_records:
            record_created_at = record.created_at
            if record_created_at.tzinfo is None:
                record_created_at = record_created_at.replace(tzinfo=timezone.utc)
            if record_created_at < snapshot_created_at:
                source_records.append(record)
        result = independently_verify_historical_freshness_verification_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        assert result.valid is True
        assert result.reconstructed_record_count == 1
    finally:
        session.close()
        engine.dispose()


def test_m4_48_detects_snapshot_tamper_with_recomputed_fingerprint():
    engine, session = _session_m4_48()
    try:
        _persist_source_verification(session)
        repository = HistoricalFreshnessVerificationHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        snapshot.record_count = 2
        snapshot.fingerprint = (
            __import__(
                "hashlib"
            ).sha256(
                __import__("json").dumps(
                    {
                        "chain_valid_count": snapshot.chain_valid_count,
                        "history_fingerprint": snapshot.history_fingerprint,
                        "integrity_version": snapshot.integrity_version,
                        "record_count": snapshot.record_count,
                        "valid_count": snapshot.valid_count,
                    },
                    ensure_ascii=True,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
        )
        session.flush()
        source_records = (
            IndependentHistoricalFreshnessReceiptVerificationRepository(session)
            .list(limit=100)[0]
        )
        result = independently_verify_historical_freshness_verification_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        assert result.valid is False
        assert "M447_RECORD_COUNT_MISMATCH" in result.blockers
    finally:
        session.close()
        engine.dispose()


def test_m4_48_fails_closed_on_invalid_source_record():
    engine, session = _session_m4_48()
    try:
        _persist_source_verification(session)
        snapshot = HistoricalFreshnessVerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        source_records = (
            IndependentHistoricalFreshnessReceiptVerificationRepository(session)
            .list(limit=100)[0]
        )
        source_records[0].verification_fingerprint = "f" * 64
        session.flush()
        with __import__("pytest").raises(
            IndependentHistoricalFreshnessVerificationHistoryIntegrityError,
            match="M4.46 source history verification record is structurally invalid",
        ):
            independently_verify_historical_freshness_verification_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_48_openapi_route_is_registered():
    from morva.api.app import app

    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/snapshots/{snapshot_id}/verify-independent"
    )
    assert "get" in app.openapi()["paths"][path]
