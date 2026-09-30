from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from morva.persistence.historical_m4_71_verification_history_integrity_m4_72 import (
    HistoricalM471VerificationHistoryIntegrityPersistenceError,
    HistoricalM471VerificationHistoryIntegrityRecord,
    HistoricalM471VerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_69_verification_receipts_m4_71 import (
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository,
)
from tests.test_independent_historical_m4_69_verification_receipts_m4_71 import (
    _session_m4_71,
)
from tests.test_historical_m4_68_verification_history_integrity_m4_69 import (
    _persist_m4_68_result,
)
from morva.persistence.historical_m4_68_verification_history_integrity_m4_69 import (
    HistoricalM468VerificationHistoryIntegrityRepository,
)


def _session_m4_72():
    engine, session = _session_m4_71()
    HistoricalM471VerificationHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_71_receipt(session, marker: str = "a" * 64):
    _persist_m4_68_result(session, marker)
    snapshot = HistoricalM468VerificationHistoryIntegrityRepository(session).capture(
        captured_by="ministry"
    )
    return IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository(
        session
    ).record(snapshot_id=snapshot.id, recorded_by="ministry")


def test_m4_72_captures_and_reverifies_m4_71_history():
    engine, session = _session_m4_72()
    try:
        first = _persist_m4_71_receipt(session)
        repository = HistoricalM471VerificationHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        integrity = snapshot.to_integrity()
        assert integrity.record_count == 1
        assert integrity.valid_count == 1
        assert repository.verify(snapshot.id).id == snapshot.id
        assert repository.capture(captured_by="ministry").id == snapshot.id
        assert first.id
    finally:
        session.close()
        engine.dispose()


def test_m4_72_preserves_point_in_time_boundary():
    engine, session = _session_m4_72()
    try:
        _persist_m4_71_receipt(session, "a" * 64)
        repository = HistoricalM471VerificationHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        _persist_m4_71_receipt(session, "b" * 64)
        assert repository.verify(first.id).id == first.id
        second = repository.capture(captured_by="ministry")
        assert second.to_integrity().record_count == 2
    finally:
        session.close()
        engine.dispose()


def test_m4_72_detects_tampered_source_receipt():
    engine, session = _session_m4_72()
    try:
        _persist_m4_71_receipt(session)
        repository = HistoricalM471VerificationHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        source = session.scalars(
            select(IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord)
        ).one()
        source.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            HistoricalM471VerificationHistoryIntegrityPersistenceError,
            match="M4.71 history reconstruction failed",
        ):
            repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_72_is_cursor_paginated():
    engine, session = _session_m4_72()
    try:
        _persist_m4_71_receipt(session, "a" * 64)
        repository = HistoricalM471VerificationHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        _persist_m4_71_receipt(session, "b" * 64)
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


def test_m4_72_rejects_invalid_cursor():
    engine, session = _session_m4_72()
    try:
        repository = HistoricalM471VerificationHistoryIntegrityRepository(session)
        with pytest.raises(
            HistoricalM471VerificationHistoryIntegrityPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalM471VerificationHistoryIntegrityPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_72_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-68-verification-history-integrity-snapshots/verification-receipt-history-integrity-snapshots"
    )
    assert "post" in paths[prefix]
    assert "get" in paths[prefix]
    assert "get" in paths[prefix + "/{snapshot_id}/verify"]
