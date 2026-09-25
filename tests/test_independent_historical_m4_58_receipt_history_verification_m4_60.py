from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.historical_m4_57_verification_receipt_history_integrity_m4_58 import (
    HistoricalM457VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_58_receipt_history_verification_m4_60 import (
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository,
)
from tests.test_historical_m4_57_verification_receipt_history_integrity_m4_58 import (
    _persist_m4_57_result,
    _session_m4_58,
)


def _session_m4_60():
    engine, session = _session_m4_58()
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_58_snapshot(session, fingerprint: str = "a" * 64):
    _persist_m4_57_result(session, fingerprint)
    return HistoricalM457VerificationReceiptHistoryIntegrityRepository(
        session
    ).capture(captured_by="ministry")


def test_m4_60_records_and_reverifies_independent_m4_59_result():
    engine, session = _session_m4_60()
    try:
        snapshot = _persist_m4_58_snapshot(session)
        repository = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(
            snapshot_id=snapshot.id,
            recorded_by="ministry",
        ).id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_60_is_cursor_paginated():
    engine, session = _session_m4_60()
    try:
        first_snapshot = _persist_m4_58_snapshot(session, "a" * 64)
        second_snapshot = _persist_m4_58_snapshot(session, "b" * 64)
        repository = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        first = repository.record(
            snapshot_id=first_snapshot.id,
            recorded_by="ministry",
        )
        second = repository.record(
            snapshot_id=second_snapshot.id,
            recorded_by="ministry",
        )
        page, has_more = repository.list(limit=1)
        assert has_more is True
        assert page[0].id == second.id
        next_page, next_has_more = repository.list(
            before_created_at=page[0].created_at,
            before_id=page[0].id,
            limit=1,
        )
        assert next_has_more is False
        assert [item.id for item in next_page] == [first.id]
    finally:
        session.close()
        engine.dispose()


def test_m4_60_fails_closed_on_tampered_receipt():
    engine, session = _session_m4_60()
    try:
        snapshot = _persist_m4_58_snapshot(session)
        repository = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError,
            match="persisted M4.60 independent verification result is structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_60_rejects_invalid_cursor():
    engine, session = _session_m4_60()
    try:
        repository = IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        with pytest.raises(
            IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_60_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    write_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-58-verification-receipts/{snapshot_id}/verification-receipts"
    )
    history_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-58-verification-receipts/verification-history"
    )
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-58-verification-receipts/verification-receipts/{verification_receipt_id}/verify"
    )
    assert "post" in paths[write_path]
    assert "get" in paths[history_path]
    assert "get" in paths[verify_path]
