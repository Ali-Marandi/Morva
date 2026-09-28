from __future__ import annotations

from datetime import datetime
import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_68_verification_history_integrity_m4_69 import (
    HistoricalM468VerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_69_verification_receipts_m4_71 import (
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository,
)
from tests.test_historical_m4_68_verification_history_integrity_m4_69 import (
    _persist_m4_68_result,
    _session_m4_69,
)


def _session_m4_71():
    engine, session = _session_m4_71()
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def test_m4_71_records_and_reverifies_independent_result():
    engine, session = _session_m4_71()
    try:
        _persist_m4_68_result(session)
        snapshot = HistoricalM468VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(snapshot_id=snapshot.id, recorded_by="ministry").id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_71_rejects_second_actor_for_same_fingerprint():
    engine, session = _session_m4_71()
    try:
        _persist_m4_68_result(session)
        snapshot = HistoricalM468VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
            session
        )
        repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        with pytest.raises(
            IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
            match="different actor",
        ):
            repository.record(snapshot_id=snapshot.id, recorded_by="auditor")
    finally:
        session.close()
        engine.dispose()


def test_m4_71_cursor_history_and_invalid_cursor():
    engine, session = _session_m4_71()
    try:
        _persist_m4_68_result(session, "a" * 64)
        first = HistoricalM468VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
            session
        )
        first_receipt = repository.record(snapshot_id=first.id, recorded_by="ministry")
        _persist_m4_68_result(session, "b" * 64)
        second = HistoricalM468VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        second_receipt = repository.record(snapshot_id=second.id, recorded_by="ministry")
        page, has_more = repository.list(limit=1)
        assert has_more is True
        assert page[0].id == second_receipt.id
        next_page, next_has_more = repository.list(
            before_created_at=page[0].created_at,
            before_id=page[0].id,
            limit=1,
        )
        assert next_has_more is False
        assert next_page[0].id == first_receipt.id
        with pytest.raises(
            IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_71_detects_tampered_receipt():
    engine, session = _session_m4_71()
    try:
        _persist_m4_68_result(session)
        snapshot = HistoricalM468VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
            match="structurally invalid|differs from reconstruction",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_71_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    prefix=(
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-68-verification-history-integrity-snapshots"
    )
    assert "post" in paths[prefix + "/{snapshot_id}/verification-receipts"]
    assert "get" in paths[prefix + "/verification-history"]
    assert "get" in paths[prefix + "/verification-receipts/{verification_id}/verify"]
