from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_71_verification_history_integrity_m4_72 import (
    HistoricalM471VerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
)
from tests.test_historical_m4_71_verification_history_integrity_m4_72 import (
    _persist_m4_71_receipt,
    _session_m4_72,
)


def _session_m4_74():
    engine, session = _session_m4_72()
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def test_m4_74_records_and_reverifies_independent_result() -> None:
    engine, session = _session_m4_74()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(snapshot_id=snapshot.id, recorded_by="ministry").id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_74_rejects_second_actor_for_same_fingerprint() -> None:
    engine, session = _session_m4_74()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        with pytest.raises(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
            match="different actor",
        ):
            repository.record(snapshot_id=snapshot.id, recorded_by="auditor")
    finally:
        session.close()
        engine.dispose()


def test_m4_74_cursor_history_and_invalid_cursor() -> None:
    engine, session = _session_m4_74()
    try:
        _persist_m4_71_receipt(session, "a" * 64)
        first = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        first_receipt = repository.record(snapshot_id=first.id, recorded_by="ministry")

        _persist_m4_71_receipt(session, "b" * 64)
        second = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
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
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_74_detects_tampered_receipt() -> None:
    engine, session = _session_m4_74()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
            match="structurally invalid|differs from reconstruction",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_74_invalid_snapshot_fails_closed() -> None:
    engine, session = _session_m4_74()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        snapshot.fingerprint = "not-a-sha"
        session.flush()
        repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        with pytest.raises(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
            match="source snapshot is structurally invalid",
        ):
            repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
    finally:
        session.close()
        engine.dispose()


def test_m4_74_openapi_routes_are_registered() -> None:
    from morva.api.app import app

    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-72-verification-history-integrity-snapshots"
    )
    paths = app.openapi()["paths"]
    assert "post" in paths[prefix + "/{snapshot_id}/verification-receipts"]
    assert "get" in paths[prefix + "/verification-history"]
    assert "get" in paths[prefix + "/verification-receipts/{verification_id}/verify"]
