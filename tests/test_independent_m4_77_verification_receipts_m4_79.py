from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475Repository,
)
from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479PersistenceError,
    IndependentM477VerificationReceiptM479Record,
    IndependentM477VerificationReceiptM479Repository,
)
from tests.test_historical_m4_72_verification_receipt_m4_75 import (
    _session_m4_75,
)
from tests.test_independent_historical_m4_72_verification_receipt_m4_75 import (
    _persist_m4_74_receipt,
)


def _session_m4_79():
    engine, session = _session_m4_75()
    IndependentM477VerificationReceiptM479Record.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_77_snapshot(session):
    _, receipt = _persist_m4_74_receipt(session)
    HistoricalM472VerificationReceiptM475Repository(session).record(
        verification_receipt_id=receipt.id,
        recorded_by="ministry",
    )
    return HistoricalM475VerificationReceiptHistoryIntegrityRepository(session).capture(
        captured_by="ministry"
    )


def test_m4_79_records_and_reverifies_result() -> None:
    engine, session = _session_m4_79()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        repository = IndependentM477VerificationReceiptM479Repository(session)
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(snapshot_id=snapshot.id, recorded_by="ministry").id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_79_rejects_second_actor_for_same_fingerprint() -> None:
    engine, session = _session_m4_79()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        repository = IndependentM477VerificationReceiptM479Repository(session)
        repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        with pytest.raises(
            IndependentM477VerificationReceiptM479PersistenceError,
            match="different actor",
        ):
            repository.record(snapshot_id=snapshot.id, recorded_by="auditor")
    finally:
        session.close()
        engine.dispose()


def test_m4_79_cursor_history_and_invalid_cursor() -> None:
    engine, session = _session_m4_79()
    try:
        first = _persist_m4_77_snapshot(session)
        repository = IndependentM477VerificationReceiptM479Repository(session)
        first_result = repository.record(snapshot_id=first.id, recorded_by="ministry")
        second = _persist_m4_77_snapshot(session)
        second_result = repository.record(snapshot_id=second.id, recorded_by="ministry")

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
            IndependentM477VerificationReceiptM479PersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentM477VerificationReceiptM479PersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_79_detects_tampered_receipt() -> None:
    engine, session = _session_m4_79()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        repository = IndependentM477VerificationReceiptM479Repository(session)
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        record.blockers_json = '[ "TAMPERED" ]'
        session.flush()
        with pytest.raises(
            IndependentM477VerificationReceiptM479PersistenceError,
            match="structurally invalid|differs from reconstruction",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_79_openapi_routes_are_registered() -> None:
    from morva.api.app import app

    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-76-verification-receipt-history-integrity-snapshots/"
        "verification-receipts"
    )
    paths = app.openapi()["paths"]
    assert "post" in paths[prefix]
    assert "get" in paths[prefix]
    assert "get" in paths[prefix + "/{verification_id}/verify"]

def test_m4_79_reverifies_and_rejects_tampered_source_result() -> None:
    engine, session = _session_m4_79()
    try:
        snapshot = _persist_m4_77_snapshot(session)
        repository = IndependentM477VerificationReceiptM479Repository(session)
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")

        source = session.scalars(
            __import__(
                "morva.persistence.historical_m4_72_verification_receipt_m4_75",
                fromlist=["HistoricalM472VerificationReceiptM475Record"],
            ).HistoricalM472VerificationReceiptM475Record
        ).first()
        assert source is not None
        source.verification_fingerprint = "f" * 64
        session.flush()

        with pytest.raises(
            IndependentM477VerificationReceiptM479PersistenceError,
            match="M4.78 independent reconstruction failed",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()

