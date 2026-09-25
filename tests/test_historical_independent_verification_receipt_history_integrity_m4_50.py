from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.historical_independent_verification_receipt_history_integrity_m4_50 import (
    HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalIndependentVerificationReceiptHistoryIntegrityRecord,
    HistoricalIndependentVerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_freshness_verification_history_integrity_receipts_m4_49 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository,
)
from tests.test_independent_historical_freshness_verification_history_integrity_receipts_m4_49 import (
    _persist_snapshot,
    _session_m4_49,
)


def _session_m4_50():
    engine, session = _session_m4_49()
    HistoricalIndependentVerificationReceiptHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_receipt(session, fingerprint: str = "a" * 64):
    snapshot = _persist_snapshot(session, fingerprint)
    return (
        IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=snapshot.id, recorded_by="ministry")
    )


def test_m4_50_captures_and_reverifies_receipt_history():
    engine, session = _session_m4_50()
    try:
        receipt = _persist_receipt(session)
        repository = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        )
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


def test_m4_50_preserves_point_in_time_boundary():
    engine, session = _session_m4_50()
    try:
        _persist_receipt(session, "a" * 64)
        repository = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        )
        first = repository.capture(captured_by="ministry")

        _persist_receipt(session, "b" * 64)
        assert repository.verify(first.id).id == first.id

        second = repository.capture(captured_by="ministry")
        assert second.to_integrity().record_count == 2
    finally:
        session.close()
        engine.dispose()


def test_m4_50_detects_tampered_m4_49_receipt():
    engine, session = _session_m4_50()
    try:
        _persist_receipt(session)
        repository = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        )
        snapshot = repository.capture(captured_by="ministry")

        source = session.scalar(
            __import__(
                "sqlalchemy",
                fromlist=["select"],
            ).select(
                IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord
            )
        )
        source.blockers_json = '["TAMPERED"]'
        session.flush()

        with pytest.raises(
            HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError,
            match="M4.49 history reconstruction failed",
        ):
            repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_50_is_cursor_paginated():
    engine, session = _session_m4_50()
    try:
        _persist_receipt(session, "a" * 64)
        repository = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        )
        first = repository.capture(captured_by="ministry")

        _persist_receipt(session, "b" * 64)
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


def test_m4_50_rejects_invalid_cursor():
    engine, session = _session_m4_50()
    try:
        repository = HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
            session
        )
        with pytest.raises(
            HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalIndependentVerificationReceiptHistoryIntegrityPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_50_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    write_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/verification-receipt-history-snapshots"
    )
    history_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/verification-receipt-history-snapshots"
    )
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "verification-receipt-history-snapshots/{snapshot_id}/verify"
    )
    assert "post" in paths[write_path]
    assert "get" in paths[history_path]
    assert "get" in paths[verify_path]
