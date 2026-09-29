from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475Repository,
)
from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM475VerificationReceiptHistoryIntegrityRecord,
    HistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from tests.test_historical_m4_72_verification_receipt_m4_75 import _session_m4_75
from tests.test_independent_historical_m4_72_verification_receipt_m4_75 import (
    _persist_m4_74_receipt,
)
from tests.test_historical_m4_72_verification_receipt_m4_75 import (
    _session_m4_75,
)


def test_m4_77_captures_and_reverifies_history() -> None:
    engine, session = _session_m4_75()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        result_repository = HistoricalM472VerificationReceiptM475Repository(session)
        result_repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )

        repository = HistoricalM475VerificationReceiptHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        assert snapshot.to_integrity().record_count == 1
        assert snapshot.to_integrity().valid_count == 1
        assert repository.verify(snapshot.id).id == snapshot.id
    finally:
        session.close()
        engine.dispose()


def test_m4_77_capture_is_fingerprint_idempotent() -> None:
    engine, session = _session_m4_75()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        HistoricalM472VerificationReceiptM475Repository(session).record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        repository = HistoricalM475VerificationReceiptHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        second = repository.capture(captured_by="ministry")
        assert second.id == first.id
    finally:
        session.close()
        engine.dispose()


def test_m4_77_cursor_history_and_invalid_cursor() -> None:
    engine, session = _session_m4_75()
    try:
        result_repository = HistoricalM472VerificationReceiptM475Repository(session)
        for fingerprint in ("a" * 64, "b" * 64):
            _, receipt = _persist_m4_74_receipt(session)
            result_repository.record(
                verification_receipt_id=receipt.id,
                recorded_by="ministry",
            )
        repository = HistoricalM475VerificationReceiptHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")
        snapshot = repository.capture(captured_by="ministry")
        assert snapshot.id == first.id

        page, has_more = repository.list(limit=1)
        assert has_more is False
        assert page[0].id == first.id

        with pytest.raises(
            HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_77_detects_tampered_source() -> None:
    engine, session = _session_m4_75()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        result_repository = HistoricalM472VerificationReceiptM475Repository(session)
        result = result_repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        repository = HistoricalM475VerificationReceiptHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        result.blockers_json = '[ "TAMPERED" ]'
        session.flush()
        with pytest.raises(
            HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
            match="M4.76 history reconstruction failed",
        ):
            repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_77_detects_tampered_snapshot() -> None:
    engine, session = _session_m4_75()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        HistoricalM472VerificationReceiptM475Repository(session).record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        repository = HistoricalM475VerificationReceiptHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        snapshot.fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
            match="persisted M4.77 receipt-history integrity is structurally invalid",
        ):
            repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_77_openapi_routes_are_registered() -> None:
    from morva.api.app import app

    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-76-verification-receipt-history-integrity-snapshots"
    )
    assert "post" in app.openapi()["paths"][prefix]
    assert "get" in app.openapi()["paths"][prefix]
    assert "get" in app.openapi()["paths"][prefix + "/{snapshot_id}/verify"]
