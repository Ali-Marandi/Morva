from __future__ import annotations

from datetime import datetime

import pytest
from morva.persistence.historical_m4_60_receipt_history_integrity_m4_61 import (
    HistoricalM460ReceiptHistoryIntegrityPersistenceError,
    HistoricalM460ReceiptHistoryIntegrityRecord,
    HistoricalM460ReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_58_receipt_history_verification_m4_60 import (
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository,
)
from tests.test_independent_historical_m4_58_receipt_history_verification_m4_60 import (
    _persist_m4_58_snapshot,
    _session_m4_60,
)


def _session_m4_61():
    engine, session = _session_m4_60()
    HistoricalM460ReceiptHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_60_receipt(session, fingerprint: str = "a" * 64):
    snapshot = _persist_m4_58_snapshot(session, fingerprint)
    return IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRepository(
        session
    ).record(snapshot_id=snapshot.id, recorded_by="ministry")


def test_m4_61_captures_and_reverifies_m4_60_receipt_history():
    engine, session = _session_m4_61()
    try:
        receipt = _persist_m4_60_receipt(session)
        repository = HistoricalM460ReceiptHistoryIntegrityRepository(session)
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


def test_m4_61_preserves_point_in_time_boundary():
    engine, session = _session_m4_61()
    try:
        _persist_m4_60_receipt(session, "a" * 64)
        repository = HistoricalM460ReceiptHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        _persist_m4_60_receipt(session, "b" * 64)
        assert repository.verify(first.id).id == first.id
        second = repository.capture(captured_by="ministry")
        assert second.to_integrity().record_count == 2
    finally:
        session.close()
        engine.dispose()


def test_m4_61_detects_tampered_m4_60_receipt():
    engine, session = _session_m4_61()
    try:
        _persist_m4_60_receipt(session)
        repository = HistoricalM460ReceiptHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        source_record = session.query(
            IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord
        ).one()
        source_record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            HistoricalM460ReceiptHistoryIntegrityPersistenceError,
            match="M4.60 history reconstruction failed",
        ):
            repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_61_is_cursor_paginated():
    engine, session = _session_m4_61()
    try:
        _persist_m4_60_receipt(session, "a" * 64)
        repository = HistoricalM460ReceiptHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        _persist_m4_60_receipt(session, "b" * 64)
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


def test_m4_61_rejects_invalid_cursor():
    engine, session = _session_m4_61()
    try:
        repository = HistoricalM460ReceiptHistoryIntegrityRepository(session)
        with pytest.raises(
            HistoricalM460ReceiptHistoryIntegrityPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalM460ReceiptHistoryIntegrityPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_61_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    write_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-60-receipt-history-integrity-snapshots"
    )
    verify_path = write_path + "/{snapshot_id}/verify"
    assert "post" in paths[write_path]
    assert "get" in paths[write_path]
    assert "get" in paths[verify_path]
