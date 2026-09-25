from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.historical_m4_63_receipt_history_integrity_m4_64 import (
    HistoricalM463ReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_64_verification_receipts_m4_66 import (
    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository,
)
from tests.test_historical_m4_63_receipt_history_integrity_m4_64 import (
    _persist_m4_63_receipt,
    _session_m4_64,
)


def _session_m4_66():
    engine, session = _session_m4_64()
    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_64_snapshot(session, fingerprint: str = "a" * 64):
    _persist_m4_63_receipt(session, fingerprint)
    return HistoricalM463ReceiptHistoryIntegrityRepository(session).capture(
        captured_by="ministry"
    )


def test_m4_66_records_and_reverifies_independent_m4_65_result():
    engine, session = _session_m4_66()
    try:
        snapshot = _persist_m4_64_snapshot(session)
        repository = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(snapshot_id=snapshot.id, recorded_by="ministry").id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_66_is_cursor_paginated_and_reverified():
    engine, session = _session_m4_66()
    try:
        first_snapshot = _persist_m4_64_snapshot(session, "a" * 64)
        second_snapshot = _persist_m4_64_snapshot(session, "b" * 64)
        repository = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        first = repository.record(snapshot_id=first_snapshot.id, recorded_by="ministry")
        second = repository.record(snapshot_id=second_snapshot.id, recorded_by="ministry")
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


def test_m4_66_preserves_snapshot_point_in_time_boundary():
    engine, session = _session_m4_66()
    try:
        snapshot = _persist_m4_64_snapshot(session, "a" * 64)
        repository = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        receipt = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        _persist_m4_64_snapshot(session, "b" * 64)
        assert repository.verify(receipt.id).id == receipt.id
        records, has_more = repository.list(snapshot_id=snapshot.id)
        assert has_more is False
        assert records[0].id == receipt.id
    finally:
        session.close()
        engine.dispose()


def test_m4_66_fails_closed_on_tampered_receipt():
    engine, session = _session_m4_66()
    try:
        snapshot = _persist_m4_64_snapshot(session)
        repository = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError,
            match="persisted M4.66 independent verification receipt is structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_66_fails_closed_on_tampered_m4_64_snapshot():
    engine, session = _session_m4_66()
    try:
        snapshot = _persist_m4_64_snapshot(session)
        repository = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        snapshot.history_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError,
            match="M4.64 source snapshot failed verification",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_66_rejects_invalid_cursor():
    engine, session = _session_m4_66()
    try:
        repository = IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        with pytest.raises(
            IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalM464ReceiptHistoryIntegrityReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_66_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    write_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-63-receipt-history-integrity-snapshots/{snapshot_id}/verification-receipts"
    )
    history_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-63-receipt-history-integrity-snapshots/verification-history"
    )
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-63-receipt-history-integrity-snapshots/verification-receipts/{verification_receipt_id}/verify"
    )
    assert "post" in paths[write_path]
    assert "get" in paths[history_path]
    assert "get" in paths[verify_path]
