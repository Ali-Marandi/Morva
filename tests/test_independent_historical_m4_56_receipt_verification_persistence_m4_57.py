from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    HistoricalM452VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_53_receipt_history_verification_m4_55 import (
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
    IndependentHistoricalM455ReceiptVerificationPersistenceError,
    IndependentHistoricalM455ReceiptVerificationRecord,
    IndependentHistoricalM455ReceiptVerificationRepository,
)
from tests.test_independent_historical_m4_53_receipt_history_verification_m4_55 import (
    _persist_m4_52_receipt,
    _session_m4_55,
)


def _session_m4_57():
    engine, session = _session_m4_55()
    IndependentHistoricalM455ReceiptVerificationRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_55_receipt(session):
    snapshot = HistoricalM452VerificationReceiptHistoryIntegrityRepository(
        session
    ).capture(captured_by="ministry")
    return IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRepository(
        session
    ).record(snapshot_id=snapshot.id, recorded_by="ministry")


def test_m4_57_records_and_reverifies_m4_56_result():
    engine, session = _session_m4_57()
    try:
        _persist_m4_52_receipt(session)
        receipt = _persist_m4_55_receipt(session)
        repository = IndependentHistoricalM455ReceiptVerificationRepository(session)
        record = repository.record(receipt_id=receipt.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(
            receipt_id=receipt.id,
            recorded_by="ministry",
        ).id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_57_is_cursor_paginated():
    engine, session = _session_m4_57()
    try:
        _persist_m4_52_receipt(session, "a" * 64)
        first_receipt = _persist_m4_55_receipt(session)
        first = IndependentHistoricalM455ReceiptVerificationRepository(session).record(
            receipt_id=first_receipt.id,
            recorded_by="ministry",
        )
        _persist_m4_52_receipt(session, "b" * 64)
        second_receipt = _persist_m4_55_receipt(session)
        second = IndependentHistoricalM455ReceiptVerificationRepository(session).record(
            receipt_id=second_receipt.id,
            recorded_by="ministry",
        )
        repository = IndependentHistoricalM455ReceiptVerificationRepository(session)
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


def test_m4_57_fails_closed_on_tampered_receipt():
    engine, session = _session_m4_57()
    try:
        _persist_m4_52_receipt(session)
        receipt = _persist_m4_55_receipt(session)
        repository = IndependentHistoricalM455ReceiptVerificationRepository(session)
        record = repository.record(receipt_id=receipt.id, recorded_by="ministry")
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM455ReceiptVerificationPersistenceError,
            match="persisted M4.57 independent verification result is structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_57_rejects_invalid_cursor():
    engine, session = _session_m4_57()
    try:
        repository = IndependentHistoricalM455ReceiptVerificationRepository(session)
        with pytest.raises(
            IndependentHistoricalM455ReceiptVerificationPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalM455ReceiptVerificationPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_57_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    base = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-54-verification-receipts/{verification_receipt_id}/"
        "independent-verification-receipts"
    )
    history = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-54-verification-receipts/independent-verification-history"
    )
    verify = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-54-verification-receipts/independent-verification-receipts/"
        "{verification_id}/verify"
    )
    assert "post" in paths[base]
    assert "get" in paths[history]
    assert "get" in paths[verify]
