from __future__ import annotations

from hashlib import sha256
import json

import pytest

from morva.persistence.historical_m4_63_receipt_history_integrity_m4_64 import (
    HistoricalM463ReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_61_receipt_history_verification_m4_63 import (
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord,
)
from morva.runtime.independent_historical_m4_64_receipt_history_verifier_m4_65 import (
    IndependentHistoricalM464ReceiptHistoryIntegrityError,
    independently_verify_historical_m4_64_receipt_history_integrity,
)
from tests.test_historical_m4_63_receipt_history_integrity_m4_64 import (
    _persist_m4_63_receipt,
    _session_m4_64,
)


def test_m4_65_independently_verifies_m4_64_snapshot():
    engine, session = _session_m4_64()
    try:
        _persist_m4_63_receipt(session)
        snapshot = HistoricalM463ReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        source_records = list(
            session.query(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = independently_verify_historical_m4_64_receipt_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        assert verification.valid is True
        assert verification.persisted_record_count == 1
        assert verification.reconstructed_record_count == 1
        assert verification.persisted_history_fingerprint == (
            verification.reconstructed_history_fingerprint
        )
        assert verification.verification_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_65_preserves_snapshot_point_in_time_boundary():
    engine, session = _session_m4_64()
    try:
        _persist_m4_63_receipt(session, "a" * 64)
        repository = HistoricalM463ReceiptHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        _persist_m4_63_receipt(session, "b" * 64)
        source_records = list(
            session.query(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = independently_verify_historical_m4_64_receipt_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        assert verification.valid is True
        assert verification.reconstructed_record_count == 1
    finally:
        session.close()
        engine.dispose()


def test_m4_65_fails_closed_on_tampered_source_record():
    engine, session = _session_m4_64()
    try:
        _persist_m4_63_receipt(session)
        snapshot = HistoricalM463ReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        source_record = session.query(
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
        ).one()
        source_record.blockers_json = '["TAMPERED"]'
        session.flush()
        source_records = list(
            session.query(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        with pytest.raises(
            IndependentHistoricalM464ReceiptHistoryIntegrityError,
            match="M4.63 source verification receipt is structurally invalid",
        ):
            independently_verify_historical_m4_64_receipt_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_65_emits_deterministic_blocker_for_snapshot_mismatch():
    engine, session = _session_m4_64()
    try:
        _persist_m4_63_receipt(session)
        snapshot = HistoricalM463ReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        snapshot.history_fingerprint = "f" * 64
        snapshot.fingerprint = sha256(
            json.dumps(
                {
                    "integrity_version": 1,
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
        source_records = list(
            session.query(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = independently_verify_historical_m4_64_receipt_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
        assert verification.valid is False
        assert verification.blockers == (
            "M464_HISTORY_FINGERPRINT_MISMATCH",
            "M464_INTEGRITY_FINGERPRINT_MISMATCH",
        )
        assert verification.verification_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_65_openapi_route_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-63-receipt-history-integrity-snapshots/{snapshot_id}/verify-independent"
    )
    assert "get" in paths[verify_path]
