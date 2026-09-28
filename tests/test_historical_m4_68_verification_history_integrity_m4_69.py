from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_68_verification_history_integrity_m4_69 import (
    HistoricalM468VerificationHistoryIntegrityPersistenceError,
    HistoricalM468VerificationHistoryIntegrityRecord,
    HistoricalM468VerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_67_verification_persistence_m4_68 import (
    IndependentHistoricalM466VerificationPersistenceReceiptRecord,
    IndependentHistoricalM466VerificationPersistenceReceiptRepository,
)
from tests.test_independent_historical_m4_67_verification_persistence_m4_68 import (
    _persist_m4_66_receipt,
    _session_m4_68,
)


def _session_m4_69():
    engine, session = _session_m4_68()
    HistoricalM468VerificationHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_68_result(session, fingerprint: str = "a" * 64):
    receipt = _persist_m4_66_receipt(session, fingerprint)
    return IndependentHistoricalM466VerificationPersistenceReceiptRepository(
        session
    ).record(
        verification_receipt_id=receipt.id,
        recorded_by="ministry",
    )


def test_m4_69_captures_and_reverifies_m4_68_history():
    engine, session = _session_m4_69()
    try:
        result = _persist_m4_68_result(session)
        repository = HistoricalM468VerificationHistoryIntegrityRepository(session)
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


def test_m4_69_preserves_point_in_time_boundary():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session, "a" * 64)
        repository = HistoricalM468VerificationHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        _persist_m4_68_result(session, "b" * 64)
        assert repository.verify(first.id).id == first.id
        second = repository.capture(captured_by="ministry")
        assert second.to_integrity().record_count == 2
    finally:
        session.close()
        engine.dispose()


def test_m4_69_detects_tampered_m4_68_result():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session)
        repository = HistoricalM468VerificationHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        source = session.scalars(
            select(IndependentHistoricalM466VerificationPersistenceReceiptRecord)
        ).one()
        source.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            HistoricalM468VerificationHistoryIntegrityPersistenceError,
            match="M4.68 history reconstruction failed",
        ):
            repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_69_is_cursor_paginated():
    engine, session = _session_m4_69()
    try:
        _persist_m4_68_result(session, "a" * 64)
        repository = HistoricalM468VerificationHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        _persist_m4_68_result(session, "b" * 64)
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


def test_m4_69_rejects_invalid_cursor():
    engine, session = _session_m4_69()
    try:
        repository = HistoricalM468VerificationHistoryIntegrityRepository(session)
        with pytest.raises(
            HistoricalM468VerificationHistoryIntegrityPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalM468VerificationHistoryIntegrityPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_69_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    base = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-68-verification-history-integrity-snapshots"
    )
    assert "post" in paths[base]
    assert "get" in paths[base]
    assert "get" in paths[base + "/{snapshot_id}/verify"]
