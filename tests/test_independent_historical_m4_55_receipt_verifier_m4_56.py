from __future__ import annotations

import pytest

from morva.persistence.historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    HistoricalM452VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_53_receipt_history_verification_m4_55 import (
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_verification_receipt_history_integrity_m4_52 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository,
)
from morva.runtime.independent_historical_m4_55_receipt_verifier_m4_56 import (
    IndependentHistoricalM455ReceiptVerificationError,
    independently_verify_historical_m4_55_receipt,
)
from tests.test_independent_historical_m4_53_receipt_history_verification_m4_55 import (
    _persist_m4_52_receipt,
    _session_m4_55,
)


def test_m4_56_independently_verifies_m4_55_receipt():
    engine, session = _session_m4_55()
    try:
        _persist_m4_52_receipt(session)
        snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        repository = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        receipt = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        source_repository = (
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
                session
            )
        )
        source_records = list(
            session.query(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        for source_record in source_records:
            source_repository.verify(source_record.id)
        verification = independently_verify_historical_m4_55_receipt(
            receipt=receipt,
            snapshot=snapshot,
            source_records=source_records,
        )
        assert verification.valid is True
        assert (
            verification.persisted_verification_fingerprint
            == verification.reconstructed_verification_fingerprint
        )
        assert verification.verification_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_56_fails_closed_on_tampered_m4_55_receipt():
    engine, session = _session_m4_55()
    try:
        _persist_m4_52_receipt(session)
        snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        receipt = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=snapshot.id, recorded_by="ministry")
        receipt.verification_fingerprint = "0" * 64
        session.flush()
        source_records = list(
            session.query(
                IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
            ).all()
        )
        with pytest.raises(
            IndependentHistoricalM455ReceiptVerificationError,
            match="persisted M4.55 verification receipt is structurally invalid",
        ):
            independently_verify_historical_m4_55_receipt(
                receipt=receipt,
                snapshot=snapshot,
                source_records=source_records,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_56_openapi_route_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-54-verification-receipts/{verification_receipt_id}/verify-independent"
    )
    assert "get" in paths[verify_path]
