from __future__ import annotations

from sqlalchemy import select
import pytest

from morva.persistence.historical_m4_71_verification_history_integrity_m4_72 import (
    HistoricalM471VerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_69_verification_receipts_m4_71 import (
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
)
from morva.runtime.independent_historical_m4_72_verification_receipt_m4_75 import (
    IndependentHistoricalM472VerificationReceiptVerificationError,
    independently_verify_historical_m4_72_verification_receipt,
)
from tests.test_independent_historical_m4_72_verification_receipts_m4_74 import (
    _persist_m4_71_receipt,
    _session_m4_74,
)


def _source_records(session):
    query = select(IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord).order_by(
        IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.created_at.asc(),
        IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.id.asc(),
    )
    return list(session.scalars(query).all())


def _persist_m4_74_receipt(session):
    _persist_m4_71_receipt(session)
    snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
        captured_by="ministry"
    )
    return (
        snapshot,
        IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(session).record(
            snapshot_id=snapshot.id,
            recorded_by="ministry",
        ),
    )


def test_m4_75_independently_verifies_m4_74_receipt() -> None:
    engine, session = _session_m4_74()
    try:
        snapshot, receipt = _persist_m4_74_receipt(session)
        result = independently_verify_historical_m4_72_verification_receipt(
            receipt=receipt,
            snapshot=snapshot,
            source_records=_source_records(session),
            source_repository=IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
                session
            ),
        )
        assert result.valid is True
        assert result.blockers == ()
        assert result.persisted_fingerprint == result.reconstructed_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_75_detects_tampered_receipt() -> None:
    engine, session = _session_m4_74()
    try:
        snapshot, receipt = _persist_m4_74_receipt(session)
        receipt.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentHistoricalM472VerificationReceiptVerificationError,
            match="persisted M4.74 verification receipt is structurally invalid",
        ):
            independently_verify_historical_m4_72_verification_receipt(
                receipt=receipt,
                snapshot=snapshot,
                source_records=_source_records(session),
                source_repository=IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
                    session
                ),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_75_detects_wrong_snapshot_binding() -> None:
    engine, session = _session_m4_74()
    try:
        snapshot, receipt = _persist_m4_74_receipt(session)
        other_snapshot, _ = _persist_m4_74_receipt(session)
        with pytest.raises(
            IndependentHistoricalM472VerificationReceiptVerificationError,
            match="snapshot binding is invalid",
        ):
            independently_verify_historical_m4_72_verification_receipt(
                receipt=receipt,
                snapshot=other_snapshot,
                source_records=_source_records(session),
                source_repository=IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
                    session
                ),
            )
        assert snapshot.id != other_snapshot.id
    finally:
        session.close()
        engine.dispose()


def test_m4_75_openapi_route_is_registered() -> None:
    from morva.api.app import app

    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-72-verification-history-integrity-snapshots/"
        "verification-receipts/{verification_id}/verify-independent"
    )
    assert "get" in app.openapi()["paths"][path]
