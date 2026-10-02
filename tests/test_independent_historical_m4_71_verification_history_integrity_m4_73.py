from __future__ import annotations

from hashlib import sha256
import json

import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_71_verification_history_integrity_m4_72 import (
    HistoricalM471VerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_69_verification_receipts_m4_71 import (
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord,
)
from morva.runtime.independent_historical_m4_71_verification_history_integrity_m4_73 import (
    IndependentHistoricalM471VerificationHistoryIntegrityError,
    independently_verify_historical_m4_71_verification_history_integrity,
)
from tests.test_historical_m4_71_verification_history_integrity_m4_72 import (
    _persist_m4_71_receipt,
    _session_m4_72,
)


def _source_records(session):
    statement = select(IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord).order_by(
        IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.created_at.asc(),
        IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.id.asc(),
    )
    return list(session.scalars(statement).all())


def test_m4_73_independently_verifies_m4_72_snapshot() -> None:
    engine, session = _session_m4_72()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        result = independently_verify_historical_m4_71_verification_history_integrity(
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


def test_m4_73_respects_snapshot_boundary() -> None:
    engine, session = _session_m4_72()
    try:
        _persist_m4_71_receipt(session, "a" * 64)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        _persist_m4_71_receipt(session, "b" * 64)
        result = independently_verify_historical_m4_71_verification_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is True
        assert result.reconstructed_record_count == 1
    finally:
        session.close()
        engine.dispose()


def test_m4_73_detects_tampered_snapshot() -> None:
    engine, session = _session_m4_72()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
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
        result = independently_verify_historical_m4_71_verification_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is False
        assert "M472_RECORD_COUNT_MISMATCH" in result.blockers
        assert "M472_INTEGRITY_FINGERPRINT_MISMATCH" in result.blockers
    finally:
        session.close()
        engine.dispose()


def test_m4_73_fails_closed_on_invalid_source_record() -> None:
    engine, session = _session_m4_72()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        source = _source_records(session)[0]
        source.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentHistoricalM471VerificationHistoryIntegrityError,
            match="M4.71 source verification record is structurally invalid",
        ):
            independently_verify_historical_m4_71_verification_history_integrity(
                snapshot=snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_73_rejects_invalid_persisted_snapshot_structure() -> None:
    engine, session = _session_m4_72()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        snapshot.fingerprint = "not-a-sha"
        session.flush()
        with pytest.raises(
            IndependentHistoricalM471VerificationHistoryIntegrityError,
            match="persisted M4.72 history integrity snapshot is structurally invalid",
        ):
            independently_verify_historical_m4_71_verification_history_integrity(
                snapshot=snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_73_openapi_route_is_registered() -> None:
    from morva.api.app import app

    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-68-verification-history-integrity-snapshots/"
        "{snapshot_id}/verify-independent-m4-72"
    )
    assert "get" in app.openapi()["paths"][path]
