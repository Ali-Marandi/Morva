from __future__ import annotations

import pytest

from morva.runtime.historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    _fingerprint,
)

from morva.persistence.historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    HistoricalM452VerificationReceiptHistoryIntegrityRecord,
    HistoricalM452VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_verification_receipt_history_integrity_m4_52 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord,
)
from morva.runtime.independent_historical_m4_52_verification_receipt_history_integrity_verifier_m4_54 import (
    IndependentHistoricalM452VerificationReceiptHistoryIntegrityError,
    independently_verify_historical_m4_52_verification_receipt_history_integrity,
)
from tests.test_historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    _persist_m4_52_receipt,
    _session_m4_53,
)


def test_m4_54_independently_verifies_m4_53_snapshot():
    engine, session = _session_m4_53()
    try:
        _persist_m4_52_receipt(session)
        snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        source_records = list(
            session.query(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = (
            independently_verify_historical_m4_52_verification_receipt_history_integrity(
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


def test_m4_54_preserves_snapshot_point_in_time_boundary():
    engine, session = _session_m4_53()
    try:
        _persist_m4_52_receipt(session, "a" * 64)
        snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        _persist_m4_52_receipt(session, "b" * 64)
        source_records = list(
            session.query(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = (
            independently_verify_historical_m4_52_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
        )
        assert verification.valid is True
        assert verification.reconstructed_record_count == 1
    finally:
        session.close()
        engine.dispose()


def test_m4_54_fails_closed_on_tampered_m4_52_source_receipt():
    engine, session = _session_m4_53()
    try:
        _persist_m4_52_receipt(session)
        snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        source_record = session.query(
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
        ).one()
        source_record.blockers_json = '["TAMPERED"]'
        session.flush()
        source_records = list(
            session.query(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        with pytest.raises(
            IndependentHistoricalM452VerificationReceiptHistoryIntegrityError,
            match="M4.52 source verification receipt is structurally invalid",
        ):
            independently_verify_historical_m4_52_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_54_emits_deterministic_blockers_for_snapshot_mismatch():
    engine, session = _session_m4_53()
    try:
        _persist_m4_52_receipt(session)
        snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        snapshot.history_fingerprint = "f" * 64
        snapshot.fingerprint = _fingerprint(
            record_count=snapshot.record_count,
            valid_count=snapshot.valid_count,
            history_fingerprint=snapshot.history_fingerprint,
        )
        session.flush()
        source_records = list(
            session.query(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = (
            independently_verify_historical_m4_52_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=source_records,
            )
        )
        assert verification.valid is False
        assert verification.blockers == (
            "M453_HISTORY_FINGERPRINT_MISMATCH",
            "M453_INTEGRITY_FINGERPRINT_MISMATCH",
        )
        assert verification.verification_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_54_openapi_route_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-52-history-integrity-snapshots/{snapshot_id}/verify-independent"
    )
    assert "get" in paths[verify_path]
