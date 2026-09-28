from __future__ import annotations

from sqlalchemy import select
import pytest

from morva.persistence.independent_historical_m4_67_verification_persistence_m4_68 import (
    IndependentHistoricalM466VerificationPersistenceReceiptRecord,
)
from morva.persistence.historical_m4_68_verification_history_integrity_m4_69 import (
    HistoricalM468VerificationHistoryIntegrityRepository,
)
from morva.runtime.independent_historical_m4_68_verification_history_integrity_m4_70 import (
    IndependentHistoricalM468VerificationHistoryIntegrityError,
    independently_verify_historical_m4_68_verification_history_integrity,
)
from tests.test_historical_m4_68_verification_history_integrity_m4_69 import (
    _persist_m4_68_result,
    _session_m4_69,
)


def _source_records(session):
    return list(
        session.scalars(
            select(IndependentHistoricalM466VerificationPersistenceReceiptRecord)
        ).order_by(
            IndependentHistoricalM466VerificationPersistenceReceiptRecord.created_at.asc(),
            IndependentHistoricalM466VerificationPersistenceReceiptRecord.id.asc(),
        )
    )


def test_m4_70_independently_verifies_m4_69_snapshot():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session)
        snapshot = HistoricalM468VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        result = independently_verify_historical_m4_68_verification_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is True
        assert result.blockers == ()
        assert result.persisted_fingerprint == result.reconstructed_fingerprint
        assert result.persisted_history_fingerprint == result.reconstructed_history_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_70_respects_snapshot_boundary():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session, "a" * 64)
        snapshot = HistoricalM468VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        _persist_m4_68_result(session, "b" * 64)
        result = independently_verify_historical_m4_68_verification_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is True
        assert result.reconstructed_record_count == 1
    finally:
        session.close()
        engine.dispose()


def test_m4_70_detects_tampered_snapshot():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session)
        snapshot = HistoricalM468VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        snapshot.record_count = 2
        session.flush()
        result = independently_verify_historical_m4_68_verification_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is False
        assert "M469_RECORD_COUNT_MISMATCH" in result.blockers
        assert "M469_INTEGRITY_FINGERPRINT_MISMATCH" in result.blockers
    finally:
        session.close()
        engine.dispose()


def test_m4_70_fails_closed_on_invalid_source_record():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session)
        snapshot = HistoricalM468VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        source = _source_records(session)[0]
        source.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentHistoricalM468VerificationHistoryIntegrityError,
            match="M4.68 source verification record is structurally invalid",
        ):
            independently_verify_historical_m4_68_verification_history_integrity(
                snapshot=snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_70_openapi_route_is_registered():
    from morva.api.app import app

    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-68-verification-history-integrity-snapshots/{snapshot_id}/verify-independent"
    )
    assert "get" in app.openapi()["paths"][path]
