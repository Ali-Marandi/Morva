from __future__ import annotations

from uuid import UUID

import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475Repository,
)
from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479Record,
    IndependentM477VerificationReceiptM479Repository,
)
from morva.runtime.historical_integrity_primitives import canonical_sha256
from morva.runtime.independent_m4_77_verification_receipt_m4_80 import (
    IndependentM477VerificationReceiptM480Error,
    independently_verify_m4_79_verification_receipt,
)
from tests.test_historical_m4_72_verification_receipt_m4_75 import _session_m4_75
from tests.test_independent_historical_m4_72_verification_receipt_m4_75 import (
    _persist_m4_74_receipt,
)
from tests.test_independent_m4_77_verification_receipts_m4_79 import (
    _persist_m4_77_snapshot,
)


def _session_m4_80():
    engine, session = _session_m4_75()
    IndependentM477VerificationReceiptM479Record.__table__.create(
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


def test_m4_80_independently_verifies_m4_79_receipt() -> None:
    engine, session = _session_m4_80()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        receipt = IndependentM477VerificationReceiptM479Repository(session).record(
            snapshot_id=snapshot.id,
            recorded_by="ministry",
        )
        result = independently_verify_m4_79_verification_receipt(
            receipt=receipt,
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is True
        assert result.blockers == ()
        assert result.persisted_fingerprint == result.reconstructed_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_80_detects_tampered_receipt() -> None:
    engine, session = _session_m4_80()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        receipt = IndependentM477VerificationReceiptM479Repository(session).record(
            snapshot_id=snapshot.id,
            recorded_by="ministry",
        )
        receipt.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentM477VerificationReceiptM480Error,
            match="persisted M4.79 verification receipt is structurally invalid",
        ):
            independently_verify_m4_79_verification_receipt(
                receipt=receipt,
                snapshot=snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_80_detects_wrong_snapshot_binding() -> None:
    engine, session = _session_m4_80()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        receipt = IndependentM477VerificationReceiptM479Repository(session).record(
            snapshot_id=snapshot.id,
            recorded_by="ministry",
        )
        other_snapshot = _persist_m4_77_snapshot(session)
        with pytest.raises(
            IndependentM477VerificationReceiptM480Error,
            match="snapshot binding is invalid",
        ):
            independently_verify_m4_79_verification_receipt(
                receipt=receipt,
                snapshot=other_snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_80_openapi_route_is_registered() -> None:
    from morva.api.app import app

    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-76-verification-receipt-history-integrity-snapshots/"
        "verification-receipts/{verification_id}/verify-independent"
    )
    assert "get" in app.openapi()["paths"][path]


def test_m4_80_verification_fingerprint_matches_canonical_sha256() -> None:
    from morva.runtime.independent_m4_77_verification_receipt_m4_80 import (
        _verification_fingerprint,
    )

    kwargs = {
        "verification_receipt_id": UUID("00000000-0000-0000-0000-000000000001"),
        "persisted_fingerprint": "1" * 64,
        "reconstructed_fingerprint": "2" * 64,
        "persisted_snapshot_id": UUID("00000000-0000-0000-0000-000000000002"),
        "reconstructed_snapshot_id": UUID("00000000-0000-0000-0000-000000000003"),
        "persisted_valid": True,
        "reconstructed_valid": True,
        "valid": True,
        "blockers": (),
    }
    payload = {
        "verification_version": 1,
        "verification_receipt_id": str(kwargs["verification_receipt_id"]),
        "persisted_fingerprint": kwargs["persisted_fingerprint"],
        "reconstructed_fingerprint": kwargs["reconstructed_fingerprint"],
        "persisted_snapshot_id": str(kwargs["persisted_snapshot_id"]),
        "reconstructed_snapshot_id": str(kwargs["reconstructed_snapshot_id"]),
        "persisted_valid": kwargs["persisted_valid"],
        "reconstructed_valid": kwargs["reconstructed_valid"],
        "valid": kwargs["valid"],
        "blockers": list(kwargs["blockers"]),
    }
    assert _verification_fingerprint(**kwargs) == canonical_sha256(payload)
