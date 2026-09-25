from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_63_receipt_history_integrity_m4_64 import (
    HistoricalM463ReceiptHistoryIntegrityPersistenceError,
    HistoricalM463ReceiptHistoryIntegrityRecord,
    HistoricalM463ReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_61_receipt_history_verification_m4_63 import (
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord,
)
from tests.test_independent_historical_m4_61_receipt_history_verification_m4_63 import (
    _persist_m4_61_snapshot,
    _session_m4_63,
)


def _session_m4_64():
    engine, session = _session_m4_63()
    HistoricalM463ReceiptHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_63_receipt(session, fingerprint: str = "a" * 64):
    snapshot = _persist_m4_61_snapshot(session, fingerprint)
    from morva.persistence.independent_historical_m4_61_receipt_history_verification_m4_63 import (
        IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository,
    )
    return IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRepository(
        session
    ).record(snapshot_id=snapshot.id, recorded_by="ministry")


def test_m4_64_captures_and_reverifies_m4_63_receipt_history():
    engine, session = _session_m4_64()
    try:
        receipt = _persist_m4_63_receipt(session)
        repository = HistoricalM463ReceiptHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        integrity = snapshot.to_integrity()
        assert integrity.record_count == 1
        assert integrity.valid_count == 1
        assert repository.verify(snapshot.id).id == snapshot.id
        assert repository.capture(captured_by="ministry").id == snapshot.id
        assert receipt.id
    finally:
        session.close()
        engine.dispose()


def test_m4_64_preserves_point_in_time_boundary():
    engine, session = _session_m4_64()
    try:
        _persist_m4_63_receipt(session, "a" * 64)
        repository = HistoricalM463ReceiptHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        _persist_m4_63_receipt(session, "b" * 64)
        assert repository.verify(first.id).id == first.id
        second = repository.capture(captured_by="ministry")
        assert second.to_integrity().record_count == 2
    finally:
        session.close()
        engine.dispose()


def test_m4_64_detects_tampered_m4_63_receipt():
    engine, session = _session_m4_64()
    try:
        _persist_m4_63_receipt(session)
        repository = HistoricalM463ReceiptHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        source_records = repository.session.scalars(
            select(IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord)
        ).all()
        source_records[0].blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            HistoricalM463ReceiptHistoryIntegrityPersistenceError,
            match="M4.63 history reconstruction failed",
        ):
            repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_64_is_cursor_paginated():
    engine, session = _session_m4_64()
    try:
        _persist_m4_63_receipt(session, "a" * 64)
        repository = HistoricalM463ReceiptHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        _persist_m4_63_receipt(session, "b" * 64)
        second = repository.capture(captured_by="ministry")
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


def test_m4_64_rejects_invalid_cursor():
    engine, session = _session_m4_64()
    try:
        repository = HistoricalM463ReceiptHistoryIntegrityRepository(session)
        with pytest.raises(
            HistoricalM463ReceiptHistoryIntegrityPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalM463ReceiptHistoryIntegrityPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_64_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    write_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-63-receipt-history-integrity-snapshots"
    )
    verify_path = write_path + "/{snapshot_id}/verify"
    assert "post" in paths[write_path]
    assert "get" in paths[write_path]
    assert "get" in paths[verify_path]
