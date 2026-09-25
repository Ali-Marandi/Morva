from __future__ import annotations

from datetime import datetime

import pytest
from morva.persistence.historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    HistoricalM452VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_53_receipt_history_verification_m4_55 import (
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRecord,
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_verification_receipt_history_integrity_m4_52 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord,
)
from tests.test_historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    _persist_m4_52_receipt,
    _session_m4_53,
)


def _session_m4_55():
    engine, session = _session_m4_53()
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def test_m4_55_records_and_reverifies_m4_54_result():
    engine, session = _session_m4_55()
    try:
        _persist_m4_52_receipt(session)
        snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        repository = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(
            snapshot_id=snapshot.id,
            recorded_by="ministry",
        )
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(
            snapshot_id=snapshot.id,
            recorded_by="ministry",
        ).id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_55_rejects_reuse_by_different_actor():
    engine, session = _session_m4_55()
    try:
        _persist_m4_52_receipt(session)
        snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        repository = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        with pytest.raises(
            IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError,
            match="already recorded by a different actor",
        ):
            repository.record(snapshot_id=snapshot.id, recorded_by="auditor")
    finally:
        session.close()
        engine.dispose()


def test_m4_55_fails_closed_on_tampered_m4_53_snapshot():
    engine, session = _session_m4_55()
    try:
        _persist_m4_52_receipt(session)
        snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        repository = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        snapshot.history_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError,
            match="M4.53 source snapshot failed verification",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_55_fails_closed_on_tampered_m4_52_source_receipt():
    engine, session = _session_m4_55()
    try:
        _persist_m4_52_receipt(session)
        snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        repository = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        source = session.query(
            IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord
        ).one()
        source.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError,
            match="M4.54 independent reconstruction failed",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_55_cursor_history():
    engine, session = _session_m4_55()
    try:
        _persist_m4_52_receipt(session, "a" * 64)
        repository = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        first_snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        first = repository.record(
            snapshot_id=first_snapshot.id,
            recorded_by="ministry",
        )

        _persist_m4_52_receipt(session, "b" * 64)
        second_snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
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


def test_m4_55_rejects_invalid_cursor():
    engine, session = _session_m4_55()
    try:
        repository = IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
            session
        )
        with pytest.raises(
            IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_55_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    record_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-53-history-integrity-snapshots/{snapshot_id}/verification-receipts"
    )
    history_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-54-verification-receipt-history"
    )
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-54-verification-receipts/{verification_receipt_id}/verify"
    )
    assert "post" in paths[record_path]
    assert "get" in paths[history_path]
    assert "get" in paths[verify_path]
