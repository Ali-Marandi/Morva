from __future__ import annotations

from hashlib import sha256
import json

import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475Repository,
)
from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from morva.runtime.independent_historical_m4_75_verification_receipt_history_integrity_m4_78 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityError,
    independently_verify_historical_m4_75_verification_receipt_history_integrity,
)
from tests.test_historical_m4_72_verification_receipt_m4_75 import (
    _session_m4_75,
)
from tests.test_independent_historical_m4_72_verification_receipt_m4_75 import (
    _persist_m4_74_receipt,
)


def _session_m4_78():
    engine, session = _session_m4_75()
    from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
        HistoricalM475VerificationReceiptHistoryIntegrityRecord,
    )
    HistoricalM475VerificationReceiptHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _source_records(session):
    from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
        HistoricalM472VerificationReceiptM475Record,
    )
    return list(
        session.scalars(select(HistoricalM472VerificationReceiptM475Record))
        .order_by(
            HistoricalM472VerificationReceiptM475Record.created_at.asc(),
            HistoricalM472VerificationReceiptM475Record.id.asc(),
        )
    )


def test_m4_78_independently_verifies_m4_77_snapshot() -> None:
    engine, session = _session_m4_78()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        HistoricalM472VerificationReceiptM475Repository(session).record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        snapshot = HistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
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


def test_m4_78_respects_snapshot_boundary() -> None:
    engine, session = _session_m4_78()
    try:
        _, first = _persist_m4_74_receipt(session)
        result_repository = HistoricalM472VerificationReceiptM475Repository(session)
        result_repository.record(verification_receipt_id=first.id, recorded_by="ministry")
        snapshot = HistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        _, second = _persist_m4_74_receipt(session)
        result_repository.record(verification_receipt_id=second.id, recorded_by="ministry")
        result = independently_verify_historical_m4_75_verification_receipt_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is True
        assert result.reconstructed_record_count == 1
    finally:
        session.close()
        engine.dispose()


def test_m4_78_detects_tampered_snapshot() -> None:
    engine, session = _session_m4_78()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        HistoricalM472VerificationReceiptM475Repository(session).record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        snapshot = HistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        snapshot.record_count = 2
        snapshot.fingerprint = sha256(
            json.dumps(
                {
                    "integrity_version": snapshot.integrity_version,
                    "record_count": snapshot.record_count,
                    "valid_count": snapshot.valid_count,
                    "history_fingerprint": snapshot.history_fingerprint,
                },
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        session.flush()
        result = independently_verify_historical_m4_75_verification_receipt_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is False
        assert "M477_RECORD_COUNT_MISMATCH" in result.blockers
        assert "M477_INTEGRITY_FINGERPRINT_MISMATCH" in result.blockers
    finally:
        session.close()
        engine.dispose()


def test_m4_78_fails_closed_on_invalid_source_record() -> None:
    engine, session = _session_m4_78()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        HistoricalM472VerificationReceiptM475Repository(session).record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        snapshot = HistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        source = _source_records(session)[0]
        source.verification_fingerprint = "f" * 64
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


def test_m4_78_rejects_invalid_persisted_snapshot_structure() -> None:
    engine, session = _session_m4_78()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        HistoricalM472VerificationReceiptM475Repository(session).record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        snapshot = HistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        snapshot.fingerprint = "not-a-sha"
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
