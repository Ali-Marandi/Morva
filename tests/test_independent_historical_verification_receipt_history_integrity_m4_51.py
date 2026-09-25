from __future__ import annotations

from hashlib import sha256
import json

import pytest

from morva.persistence.historical_independent_verification_receipt_history_integrity_m4_50 import (
    HistoricalIndependentVerificationReceiptHistoryIntegrityRepository,
)
from morva.runtime.independent_historical_verification_receipt_history_integrity_verifier_m4_51 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrityError,
    independently_verify_historical_independent_verification_receipt_history_integrity,
)
from morva.persistence.independent_historical_freshness_verification_history_integrity_receipts_m4_49 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord,
)
from tests.test_historical_independent_verification_receipt_history_integrity_m4_50 import (
    _persist_receipt,
    _session_m4_50,
)


def test_m4_51_independently_verifies_m4_50_snapshot():
    engine, session = _session_m4_50()
    try:
        _persist_receipt(session)
        snapshot = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        source_records = list(
            session.query(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = (
            independently_verify_historical_independent_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
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


def test_m4_51_preserves_snapshot_point_in_time_boundary():
    engine, session = _session_m4_50()
    try:
        _persist_receipt(session, "a" * 64)
        repository = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        )
        snapshot = repository.capture(captured_by="ministry")
        _persist_receipt(session, "b" * 64)
        source_records = list(
            session.query(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = (
            independently_verify_historical_independent_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
        )
        assert verification.valid is True
        assert verification.reconstructed_record_count == 1
    finally:
        session.close()
        engine.dispose()


def test_m4_51_fails_closed_on_tampered_source_record():
    engine, session = _session_m4_50()
    try:
        receipt = _persist_receipt(session)
        snapshot = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        receipt.blockers_json = '[\"TAMPERED\"]'
        session.flush()
        source_records = list(
            session.query(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord
            ).all()
        )
        with pytest.raises(
            IndependentHistoricalVerificationReceiptHistoryIntegrityError,
            match="M4.49 source receipt-history record is structurally invalid",
        ):
            independently_verify_historical_independent_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_51_emits_deterministic_blocker_for_snapshot_mismatch():
    engine, session = _session_m4_50()
    try:
        _persist_receipt(session)
        snapshot = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
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
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = (
            independently_verify_historical_independent_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
        )
        assert verification.valid is False
        assert verification.blockers == (
            "M450_HISTORY_FINGERPRINT_MISMATCH",
            "M450_INTEGRITY_FINGERPRINT_MISMATCH",
        )
        assert verification.verification_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_51_openapi_route_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "verification-receipt-history-snapshots/{snapshot_id}/verify-independent"
    )
    assert "get" in paths[verify_path]
