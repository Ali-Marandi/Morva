from __future__ import annotations

from uuid import uuid4

import pytest

from morva.persistence.independent_historical_m4_61_receipt_history_verification_m4_63 import (
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord,
)
from morva.persistence.independent_historical_m4_64_verification_receipts_m4_66 import (
    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository,
)
from morva.runtime.independent_historical_m4_66_receipt_verifier_m4_67 import (
    IndependentHistoricalM466ReceiptVerificationError,
    independently_verify_historical_m4_66_receipt,
)
from tests.test_independent_historical_m4_64_verification_receipts_m4_66 import (
    _persist_m4_64_snapshot,
    _session_m4_66,
)


def test_m4_67_independently_verifies_m4_66_receipt():
    engine, session = _session_m4_66()
    try:
        snapshot = _persist_m4_64_snapshot(session)
        receipt = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=snapshot.id, recorded_by="ministry")
        source_records = list(
            session.query(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = independently_verify_historical_m4_66_receipt(
            receipt=receipt,
            snapshot=snapshot,
            source_records=source_records,
        )
        assert verification.valid is True
        assert verification.receipt_id == receipt.id
        assert (
            verification.persisted_verification_fingerprint
            == verification.reconstructed_verification_fingerprint
        )
        assert verification.verification_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_67_fails_closed_on_tampered_m4_66_receipt():
    engine, session = _session_m4_66()
    try:
        snapshot = _persist_m4_64_snapshot(session)
        receipt = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=snapshot.id, recorded_by="ministry")
        receipt.verification_fingerprint = "f" * 64
        session.flush()
        source_records = list(
            session.query(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        with pytest.raises(
            IndependentHistoricalM466ReceiptVerificationError,
            match="persisted M4.66 verification receipt is structurally invalid",
        ):
            independently_verify_historical_m4_66_receipt(
                receipt=receipt,
                snapshot=snapshot,
                source_records=source_records,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_67_emits_deterministic_receipt_mismatch():
    engine, session = _session_m4_66()
    try:
        snapshot = _persist_m4_64_snapshot(session)
        receipt = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=snapshot.id, recorded_by="ministry")
        receipt.snapshot_id = uuid4()
        session.flush()
        source_records = list(
            session.query(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        verification = independently_verify_historical_m4_66_receipt(
            receipt=receipt,
            snapshot=snapshot,
            source_records=source_records,
        )
        assert verification.valid is False
        assert verification.blockers == (
            "M466_SNAPSHOT_ID_MISMATCH",
            "M466_VERIFICATION_RESULT_MISMATCH",
        )
        assert verification.verification_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_67_reverifies_source_chain():
    engine, session = _session_m4_66()
    try:
        snapshot = _persist_m4_64_snapshot(session)
        receipt = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=snapshot.id, recorded_by="ministry")
        source = session.query(
            IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
        ).one()
        source.blockers_json = '["TAMPERED"]'
        session.flush()
        source_records = list(
            session.query(
                IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        with pytest.raises(
            IndependentHistoricalM466ReceiptVerificationError,
            match="independent M4.65 reconstruction failed",
        ):
            independently_verify_historical_m4_66_receipt(
                receipt=receipt,
                snapshot=snapshot,
                source_records=source_records,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_67_openapi_route_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-63-receipt-history-integrity-snapshots/verification-receipts/"
        "{verification_receipt_id}/verify-independent"
    )
    assert "get" in paths[verify_path]
