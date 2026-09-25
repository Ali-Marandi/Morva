from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.independent_historical_m4_64_verification_receipts_m4_66 import (
    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_m4_67_verification_persistence_m4_68 import (
    IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError,
    IndependentHistoricalM466VerificationPersistenceReceiptRecord,
    IndependentHistoricalM466VerificationPersistenceReceiptRepository,
)
from tests.test_independent_historical_m4_64_verification_receipts_m4_66 import (
    _persist_m4_64_snapshot,
    _session_m4_66,
)


def _session_m4_68():
    engine, session = _session_m4_66()
    IndependentHistoricalM466VerificationPersistenceReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_66_receipt(session, fingerprint: str = "a" * 64):
    snapshot = _persist_m4_64_snapshot(session, fingerprint)
    return IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRepository(
        session
    ).record(snapshot_id=snapshot.id, recorded_by="ministry")


def test_m4_68_records_and_reverifies_m4_67_result():
    engine, session = _session_m4_68()
    try:
        receipt = _persist_m4_66_receipt(session)
        repository = IndependentHistoricalM466VerificationPersistenceReceiptRepository(
            session
        )
        record = repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        ).id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_68_is_cursor_paginated():
    engine, session = _session_m4_68()
    try:
        first_receipt = _persist_m4_66_receipt(session, "a" * 64)
        first = IndependentHistoricalM466VerificationPersistenceReceiptRepository(
            session
        ).record(
            verification_receipt_id=first_receipt.id,
            recorded_by="ministry",
        )
        second_receipt = _persist_m4_66_receipt(session, "b" * 64)
        second = IndependentHistoricalM466VerificationPersistenceReceiptRepository(
            session
        ).record(
            verification_receipt_id=second_receipt.id,
            recorded_by="ministry",
        )
        repository = IndependentHistoricalM466VerificationPersistenceReceiptRepository(
            session
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


def test_m4_68_fails_closed_on_tampered_result():
    engine, session = _session_m4_68()
    try:
        receipt = _persist_m4_66_receipt(session)
        repository = IndependentHistoricalM466VerificationPersistenceReceiptRepository(
            session
        )
        record = repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError,
            match="persisted M4.68 independent verification result is structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_68_fails_closed_on_tampered_source_receipt():
    engine, session = _session_m4_68()
    try:
        receipt = _persist_m4_66_receipt(session)
        repository = IndependentHistoricalM466VerificationPersistenceReceiptRepository(
            session
        )
        record = repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        receipt.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError,
            match="M4.66 source verification receipt failed verification",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_68_rejects_invalid_cursor():
    engine, session = _session_m4_68()
    try:
        repository = IndependentHistoricalM466VerificationPersistenceReceiptRepository(
            session
        )
        with pytest.raises(
            IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalM466VerificationPersistenceReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_68_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    base = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-63-receipt-history-integrity-snapshots/verification-receipts/"
        "{verification_receipt_id}/independent-verification-receipts"
    )
    history = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-63-receipt-history-integrity-snapshots/verification-receipts/"
        "independent-verification-history"
    )
    verify = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-63-receipt-history-integrity-snapshots/verification-receipts/"
        "independent-verification-receipts/{verification_id}/verify"
    )
    assert "post" in paths[base]
    assert "get" in paths[history]
    assert "get" in paths[verify]
