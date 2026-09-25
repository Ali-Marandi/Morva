from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.historical_independent_verification_receipt_history_integrity_m4_50 import (
    HistoricalIndependentVerificationReceiptHistoryIntegrityRecord,
    HistoricalIndependentVerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_verification_receipt_history_integrity_m4_52 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository,
)
from tests.test_historical_independent_verification_receipt_history_integrity_m4_50 import (
    _persist_receipt,
    _session_m4_50,
)


def _session_m4_52():
    engine, session = _session_m4_50()
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_50_snapshot(session, fingerprint: str = "a" * 64):
    _persist_receipt(session, fingerprint)
    return HistoricalIndependentVerificationReceiptHistoryIntegrityRepository(
        session
    ).capture(captured_by="ministry")


def test_m4_52_records_and_reverifies_independent_m4_51_result():
    engine, session = _session_m4_52()
    try:
        snapshot = _persist_m4_50_snapshot(session)
        repository = IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(snapshot_id=snapshot.id, recorded_by="ministry").id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_52_is_cursor_paginated_and_reverified():
    engine, session = _session_m4_52()
    try:
        first = _persist_m4_50_snapshot(session, "a" * 64)
        second = _persist_m4_50_snapshot(session, "b" * 64)
        repository = IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
            session
        )
        first_receipt = repository.record(snapshot_id=first.id, recorded_by="ministry")
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
        assert [item.id for item in next_page] == [first_receipt.id]
    finally:
        session.close()
        engine.dispose()


def test_m4_52_preserves_snapshot_point_in_time_boundary():
    engine, session = _session_m4_52()
    try:
        first = _persist_m4_50_snapshot(session, "a" * 64)
        repository = IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
            session
        )
        first_receipt = repository.record(snapshot_id=first.id, recorded_by="ministry")
        _persist_m4_50_snapshot(session, "b" * 64)
        assert repository.verify(first_receipt.id).id == first_receipt.id
        assert repository.list(snapshot_id=first.id)[0].id == first_receipt.id
    finally:
        session.close()
        engine.dispose()


def test_m4_52_fails_closed_on_tampered_receipt():
    engine, session = _session_m4_52()
    try:
        snapshot = _persist_m4_50_snapshot(session)
        repository = IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        record.blockers_json = '[\"TAMPERED\"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
            match="persisted M4.52 independent verification receipt is structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_52_fails_closed_on_tampered_m4_50_snapshot():
    engine, session = _session_m4_52()
    try:
        snapshot = _persist_m4_50_snapshot(session)
        repository = IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        snapshot.history_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
            match="M4.50 source snapshot failed verification",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_52_rejects_invalid_cursor():
    engine, session = _session_m4_52()
    try:
        repository = IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRepository(
            session
        )
        with pytest.raises(
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_52_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    write_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "verification-receipt-history-integrity/snapshots/{snapshot_id}/verification-receipts"
    )
    history_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "verification-receipt-history-integrity/verification-history"
    )
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "verification-receipt-history-integrity/verification-receipts/{verification_receipt_id}/verify"
    )
    assert "post" in paths[write_path]
    assert "get" in paths[history_path]
    assert "get" in paths[verify_path]
