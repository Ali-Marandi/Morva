from __future__ import annotations

import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475Record,
)
from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479Record,
    IndependentM477VerificationReceiptM479Repository,
)
from morva.persistence.independent_m4_79_verification_receipts_m4_81 import (
    IndependentM479VerificationReceiptM481Record,
    IndependentM479VerificationReceiptM481Repository,
)
from morva.runtime.independent_m4_77_verification_receipt_m4_80 import (
    _verification_fingerprint,
)
from morva.runtime.independent_m4_79_verification_receipt_m4_82 import (
    IndependentM481VerificationReceiptM482Error,
    independently_verify_m4_81_verification_receipt,
)
from tests.test_independent_m4_77_verification_receipts_m4_79 import (
    _persist_m4_77_snapshot,
)
from tests.test_historical_m4_72_verification_receipt_m4_75 import _session_m4_75


def _session_m4_82():
    engine, session = _session_m4_75()
    for model in (
        HistoricalM475VerificationReceiptHistoryIntegrityRecord,
        IndependentM477VerificationReceiptM479Record,
        IndependentM479VerificationReceiptM481Record,
    ):
        model.__table__.create(bind=engine, checkfirst=True)
    return engine, session


def _source_records(session):
    return list(
        session.scalars(
            select(HistoricalM472VerificationReceiptM475Record).order_by(
                HistoricalM472VerificationReceiptM475Record.created_at.asc(),
                HistoricalM472VerificationReceiptM475Record.id.asc(),
            )
        )
    )


def _persist_m4_81_receipt(session):
    snapshot = _persist_m4_77_snapshot(session)
    m4_79 = IndependentM477VerificationReceiptM479Repository(session).record(
        snapshot_id=snapshot.id,
        recorded_by="ministry",
    )
    m4_81 = IndependentM479VerificationReceiptM481Repository(session).record(
        verification_receipt_id=m4_79.id,
        recorded_by="ministry",
    )
    return snapshot, m4_79, m4_81


def test_m4_82_independently_verifies_m4_81_receipt() -> None:
    engine, session = _session_m4_82()
    try:
        snapshot, m4_79, m4_81 = _persist_m4_81_receipt(session)
        result = independently_verify_m4_81_verification_receipt(
            receipt=m4_81,
            source_receipt=m4_79,
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is True
        assert result.blockers == ()
        assert result.persisted_fingerprint == result.reconstructed_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_82_detects_tampered_m4_81_receipt() -> None:
    engine, session = _session_m4_82()
    try:
        snapshot, m4_79, m4_81 = _persist_m4_81_receipt(session)
        m4_81.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentM481VerificationReceiptM482Error,
            match="persisted M4.81 verification receipt is structurally invalid",
        ):
            independently_verify_m4_81_verification_receipt(
                receipt=m4_81,
                source_receipt=m4_79,
                snapshot=snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_82_detects_tampered_m4_79_source() -> None:
    engine, session = _session_m4_82()
    try:
        snapshot, m4_79, m4_81 = _persist_m4_81_receipt(session)
        m4_79.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentM481VerificationReceiptM482Error,
            match="M4.79 source verification receipt is structurally invalid",
        ):
            independently_verify_m4_81_verification_receipt(
                receipt=m4_81,
                source_receipt=m4_79,
                snapshot=snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_82_emits_deterministic_validity_blocker() -> None:
    engine, session = _session_m4_82()
    try:
        snapshot, m4_79, m4_81 = _persist_m4_81_receipt(session)
        stored = m4_81.to_verification()
        m4_81.persisted_valid = not stored.persisted_valid
        m4_81.verification_fingerprint = _verification_fingerprint(
            verification_receipt_id=stored.verification_receipt_id,
            persisted_fingerprint=stored.verification_fingerprint,
            reconstructed_fingerprint=stored.reconstructed_fingerprint,
            persisted_snapshot_id=stored.persisted_snapshot_id,
            reconstructed_snapshot_id=stored.reconstructed_snapshot_id,
            persisted_valid=m4_81.persisted_valid,
            reconstructed_valid=stored.reconstructed_valid,
            valid=stored.valid,
            blockers=stored.blockers,
        )
        session.flush()
        result = independently_verify_m4_81_verification_receipt(
            receipt=m4_81,
            source_receipt=m4_79,
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is False
        assert "M481_PERSISTED_VALIDITY_MISMATCH" in result.blockers
    finally:
        session.close()
        engine.dispose()


def test_m4_82_openapi_route_is_registered() -> None:
    from morva.api.app import app

    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-76-verification-receipt-history-integrity-snapshots/"
        "independent-verification-receipts/{verification_id}/verify-independent"
    )
    assert "get" in app.openapi()["paths"][path]
