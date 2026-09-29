from __future__ import annotations

from sqlalchemy import select
import pytest

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475Record,
    HistoricalM472VerificationReceiptM475Repository,
)
from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from morva.runtime.independent_historical_m4_75_verification_receipt_history_integrity_m4_78 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityError,
    independently_verify_historical_m4_75_verification_receipt_history_integrity,
)
from tests.test_historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    _persist_m4_74_receipt,
)
from tests.test_historical_m4_72_verification_receipt_m4_75 import (
    _session_m4_75,
)


def _source_records(session):
    return list(
        session.scalars(
            select(HistoricalM472VerificationReceiptM475Record).order_by(
                HistoricalM472VerificationReceiptM475Record.created_at.asc(),
                HistoricalM472VerificationReceiptM475Record.id.asc(),
            )
        )
    )


def _persist_m4_77_snapshot(session):
    _, receipt = _persist_m4_74_receipt(session)
    HistoricalM472VerificationReceiptM475Repository(session).record(
        verification_receipt_id=receipt.id,
        recorded_by="ministry",
    )
    return HistoricalM475VerificationReceiptHistoryIntegrityRepository(session).capture(
        captured_by="ministry"
    )


def test_m4_78_independently_verifies_m4_77_snapshot() -> None:
    engine, session = _session_m4_75()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        result = independently_verify_historical_m4_75_verification_receipt_history_integrity(
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


def test_m4_78_detects_tampered_snapshot_structure() -> None:
    engine, session = _session_m4_75()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        snapshot.fingerprint = "f" * 64
        session.flush()

        with pytest.raises(
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityError,
            match="persisted M4.77 receipt-history integrity snapshot is structurally invalid",
        ):
            independently_verify_historical_m4_75_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_78_detects_source_tampering() -> None:
    engine, session = _session_m4_75()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        source = _source_records(session)[0]
        source.blockers_json = '["M478_TAMPERED"]'
        session.flush()

        with pytest.raises(
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityError,
            match="M4.76 source verification result is structurally invalid",
        ):
            independently_verify_historical_m4_75_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_78_reports_deterministic_mismatch_blockers() -> None:
    engine, session = _session_m4_75()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        source = _source_records(session)[0]
        source.recorded_by = "different-actor"
        session.flush()

        result = independently_verify_historical_m4_75_verification_receipt_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is False
        assert "M477_HISTORY_FINGERPRINT_MISMATCH" in result.blockers
        assert "M477_INTEGRITY_FINGERPRINT_MISMATCH" in result.blockers
    finally:
        session.close()
        engine.dispose()


def test_m4_78_openapi_route_is_registered() -> None:
    from morva.api.app import app

    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-76-verification-receipt-history-integrity-snapshots/"
        "{snapshot_id}/verify-independent"
    )
    assert "get" in app.openapi()["paths"][path]
