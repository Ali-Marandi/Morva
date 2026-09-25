from __future__ import annotations

from hashlib import sha256
import json

import pytest

from morva.persistence.independent_historical_m4_58_receipt_history_verification_m4_60 import (
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord,
)
from morva.runtime.independent_historical_m4_60_verifier_m4_61 import (
    IndependentHistoricalM460VerificationError,
    independently_verify_historical_m4_60_result,
)
from tests.test_independent_historical_m4_58_receipt_history_verification_m4_60 import (
    _persist_m4_58_snapshot,
    _session_m4_60,
)


def test_m4_61_independently_verifies_m4_60_result():
    engine, session = _session_m4_60()
    try:
        snapshot = _persist_m4_58_snapshot(session)
        from morva.persistence.independent_historical_m4_58_receipt_history_verification_m4_60 import (
            IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository,
        )

        receipt = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=snapshot.id, recorded_by="ministry")
        from morva.persistence.historical_m4_57_verification_receipt_history_integrity_m4_58 import (
            HistoricalM457VerificationReceiptHistoryIntegrityRepository,
        )
        historical_snapshot = HistoricalM457VerificationReceiptHistoryIntegrityRepository(
            session
        ).get if False else None
        source_records = []
        from morva.persistence.independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
            IndependentHistoricalM455ReceiptVerificationRecord,
        )
        source_records = list(
            session.query(IndependentHistoricalM455ReceiptVerificationRecord).all()
        )
        from morva.persistence.historical_m4_57_verification_receipt_history_integrity_m4_58 import (
            HistoricalM457VerificationReceiptHistoryIntegrityRecord,
        )
        m458_snapshot = session.get(
            HistoricalM457VerificationReceiptHistoryIntegrityRecord,
            receipt.snapshot_id,
        )
        verification = independently_verify_historical_m4_60_result(
            receipt=receipt,
            snapshot=m458_snapshot,
            source_records=source_records,
        )
        assert verification.blockers == ()
        assert verification.persisted_verification_fingerprint == (
            verification.reconstructed_verification_fingerprint
        )
        assert verification.verification_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_61_fails_closed_on_tampered_m4_60_receipt():
    engine, session = _session_m4_60()
    try:
        snapshot = _persist_m4_58_snapshot(session)
        from morva.persistence.independent_historical_m4_58_receipt_history_verification_m4_60 import (
            IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository,
        )
        receipt = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=snapshot.id, recorded_by="ministry")
        receipt.blockers_json = '["TAMPERED"]'
        session.flush()
        from morva.persistence.historical_m4_57_verification_receipt_history_integrity_m4_58 import (
            HistoricalM457VerificationReceiptHistoryIntegrityRecord,
        )
        from morva.persistence.independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
            IndependentHistoricalM455ReceiptVerificationRecord,
        )
        with pytest.raises(
            IndependentHistoricalM460VerificationError,
            match="persisted M4.60 verification receipt is structurally invalid",
        ):
            independently_verify_historical_m4_60_result(
                receipt=receipt,
                snapshot=session.get(
                    HistoricalM457VerificationReceiptHistoryIntegrityRecord,
                    receipt.snapshot_id,
                ),
                source_records=list(
                    session.query(IndependentHistoricalM455ReceiptVerificationRecord).all()
                ),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_61_emits_deterministic_blocker_for_snapshot_mismatch():
    engine, session = _session_m4_60()
    try:
        snapshot = _persist_m4_58_snapshot(session)
        from morva.persistence.independent_historical_m4_58_receipt_history_verification_m4_60 import (
            IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository,
        )
        receipt = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=snapshot.id, recorded_by="ministry")
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
        from morva.persistence.historical_m4_57_verification_receipt_history_integrity_m4_58 import (
            HistoricalM457VerificationReceiptHistoryIntegrityRecord,
        )
        from morva.persistence.independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
            IndependentHistoricalM455ReceiptVerificationRecord,
        )
        verification = independently_verify_historical_m4_60_result(
            receipt=receipt,
            snapshot=session.get(
                HistoricalM457VerificationReceiptHistoryIntegrityRecord,
                receipt.snapshot_id,
            ),
            source_records=list(
                session.query(IndependentHistoricalM455ReceiptVerificationRecord).all()
            ),
        )
        assert verification.blockers == (
            "M460_VERIFICATION_FINGERPRINT_MISMATCH",
            "M460_VERIFICATION_RESULT_MISMATCH",
        )
    finally:
        session.close()
        engine.dispose()


def test_m4_61_openapi_route_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-58-verification-receipts/verification-receipts/"
        "{verification_receipt_id}/verify-independent"
    )
    assert "get" in paths[verify_path]
