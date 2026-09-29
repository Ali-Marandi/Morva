from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479Repository,
)
from morva.persistence.independent_m4_79_verification_receipts_m4_81 import (
    IndependentM479VerificationReceiptM481PersistenceError,
    IndependentM479VerificationReceiptM481Record,
    IndependentM479VerificationReceiptM481Repository,
)
from tests.test_independent_m4_77_verification_receipts_m4_79 import (
    _persist_m4_77_snapshot,
)
from tests.test_independent_historical_m4_72_verification_receipt_m4_75 import (
    _persist_m4_74_receipt,
)
from tests.test_historical_m4_72_verification_receipt_m4_75 import _session_m4_75


def _session_m4_81():
    engine, session = _session_m4_75()
    IndependentM479VerificationReceiptM481Record.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_79_receipt(session):
    snapshot = _persist_m4_77_snapshot(session)
    return IndependentM477VerificationReceiptM479Repository(session).record(
        snapshot_id=snapshot.id,
        recorded_by="ministry",
    )


def test_m4_81_records_and_reverifies_result() -> None:
    engine, session = _session_m4_81()
    try:
        receipt = _persist_m4_79_receipt(session)
        repository = IndependentM479VerificationReceiptM481Repository(session)
        record = repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        ).id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_81_rejects_second_actor_for_same_fingerprint() -> None:
    engine, session = _session_m4_81()
    try:
        receipt = _persist_m4_79_receipt(session)
        repository = IndependentM479VerificationReceiptM481Repository(session)
        repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        with pytest.raises(
            IndependentM479VerificationReceiptM481PersistenceError,
            match="different actor",
        ):
            repository.record(
                verification_receipt_id=receipt.id,
                recorded_by="auditor",
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_81_cursor_history_and_invalid_cursor() -> None:
    engine, session = _session_m4_81()
    try:
        first = _persist_m4_79_receipt(session)
        second = _persist_m4_79_receipt(session)
        repository = IndependentM479VerificationReceiptM481Repository(session)
        first_result = repository.record(
            verification_receipt_id=first.id,
            recorded_by="ministry",
        )
        second_result = repository.record(
            verification_receipt_id=second.id,
            recorded_by="ministry",
        )
        page, has_more = repository.list(limit=1)
        assert has_more is True
        assert page[0].id == second_result.id
        next_page, next_has_more = repository.list(
            before_created_at=page[0].created_at,
            before_id=page[0].id,
            limit=1,
        )
        assert next_has_more is False
        assert next_page[0].id == first_result.id
        with pytest.raises(
            IndependentM479VerificationReceiptM481PersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentM479VerificationReceiptM481PersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_81_detects_tampered_receipt() -> None:
    engine, session = _session_m4_81()
    try:
        receipt = _persist_m4_79_receipt(session)
        repository = IndependentM479VerificationReceiptM481Repository(session)
        record = repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        record.blockers_json = '[ "TAMPERED" ]'
        session.flush()
        with pytest.raises(
            IndependentM479VerificationReceiptM481PersistenceError,
            match="structurally invalid|differs from reconstruction",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_81_openapi_routes_are_registered() -> None:
    from morva.api.app import app

    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-76-verification-receipt-history-integrity-snapshots/"
        "independent-verification-receipts"
    )
    paths = app.openapi()["paths"]
    assert "post" in paths[prefix + "/{verification_receipt_id}"]
    assert "get" in paths[prefix]
    assert "get" in paths[prefix + "/{verification_id}/verify"]
