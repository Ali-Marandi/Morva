from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_57_verification_receipt_history_integrity_m4_58 import (
    HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM457VerificationReceiptHistoryIntegrityRecord,
    HistoricalM457VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
    IndependentHistoricalM455ReceiptVerificationRecord,
    IndependentHistoricalM455ReceiptVerificationRepository,
)
from tests.test_independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
    _persist_m4_55_receipt,
    _session_m4_57,
)
from tests.test_independent_historical_m4_53_receipt_history_verification_m4_55 import (
    _persist_m4_52_receipt,
)


def _session_m4_58():
    engine, session = _session_m4_57()
    HistoricalM457VerificationReceiptHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_57_result(session, fingerprint: str = "a" * 64):
    _persist_m4_52_receipt(session, fingerprint)
    receipt = _persist_m4_55_receipt(session)
    return IndependentHistoricalM455ReceiptVerificationRepository(session).record(
        receipt_id=receipt.id,
        recorded_by="ministry",
    )


def test_m4_58_captures_and_reverifies_m4_57_receipt_history():
    engine, session = _session_m4_58()
    try:
        result = _persist_m4_57_result(session)
        repository = HistoricalM457VerificationReceiptHistoryIntegrityRepository(
            session
        )
        snapshot = repository.capture(captured_by="ministry")
        integrity = snapshot.to_integrity()
        assert integrity.record_count == 1
        assert integrity.valid_count == 1
        assert repository.verify(snapshot.id).id == snapshot.id
        assert repository.capture(captured_by="ministry").id == snapshot.id
        assert result.id
    finally:
        session.close()
        engine.dispose()


def test_m4_58_preserves_point_in_time_boundary():
    engine, session = _session_m4_58()
    try:
        _persist_m4_57_result(session, "a" * 64)
        repository = HistoricalM457VerificationReceiptHistoryIntegrityRepository(
            session
        )
        first = repository.capture(captured_by="ministry")
        _persist_m4_57_result(session, "b" * 64)
        assert repository.verify(first.id).id == first.id
        second = repository.capture(captured_by="ministry")
        assert second.to_integrity().record_count == 2
    finally:
        session.close()
        engine.dispose()


def test_m4_58_detects_tampered_m4_57_receipt():
    engine, session = _session_m4_58()
    try:
        _persist_m4_57_result(session)
        repository = HistoricalM457VerificationReceiptHistoryIntegrityRepository(
            session
        )
        snapshot = repository.capture(captured_by="ministry")
        source = session.scalars(
            select(IndependentHistoricalM455ReceiptVerificationRecord)
        ).one()
        source.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError,
            match="M4.57 history reconstruction failed",
        ):
            repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_58_is_cursor_paginated():
    engine, session = _session_m4_58()
    try:
        _persist_m4_57_result(session, "a" * 64)
        repository = HistoricalM457VerificationReceiptHistoryIntegrityRepository(
            session
        )
        first = repository.capture(captured_by="ministry")
        _persist_m4_57_result(session, "b" * 64)
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


def test_m4_58_rejects_invalid_cursor():
    engine, session = _session_m4_58()
    try:
        repository = HistoricalM457VerificationReceiptHistoryIntegrityRepository(
            session
        )
        with pytest.raises(
            HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_58_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    base = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-57-verification-history-integrity-snapshots"
    )
    assert "post" in paths[base]
    assert "get" in paths[base]
    assert "get" in paths[base + "/{snapshot_id}/verify"]
