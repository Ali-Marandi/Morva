from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475PersistenceError,
    HistoricalM472VerificationReceiptM475Record,
    HistoricalM472VerificationReceiptM475Repository,
)
from morva.persistence.historical_m4_71_verification_history_integrity_m4_72 import (
    HistoricalM471VerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
)
from tests.test_historical_m4_71_verification_history_integrity_m4_72 import (
    _persist_m4_71_receipt,
)
from tests.test_independent_historical_m4_72_verification_receipt_m4_75 import (
    _persist_m4_74_receipt,
)
from tests.test_independent_historical_m4_72_verification_receipts_m4_74 import (
    _session_m4_74,
)


def _session_m4_75():
    engine, session = _session_m4_74()
    HistoricalM472VerificationReceiptM475Record.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def test_m4_76_records_and_reverifies_m4_75_result() -> None:
    engine, session = _session_m4_75()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        repository = HistoricalM472VerificationReceiptM475Repository(session)
        record = repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert (
            repository.record(
                verification_receipt_id=receipt.id,
                recorded_by="ministry",
            ).id
            == record.id
        )
    finally:
        session.close()
        engine.dispose()


def test_m4_76_rejects_second_actor_for_same_fingerprint() -> None:
    engine, session = _session_m4_75()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        repository = HistoricalM472VerificationReceiptM475Repository(session)
        repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        with pytest.raises(
            HistoricalM472VerificationReceiptM475PersistenceError,
            match="different actor",
        ):
            repository.record(
                verification_receipt_id=receipt.id,
                recorded_by="auditor",
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_76_cursor_history_and_invalid_cursor() -> None:
    engine, session = _session_m4_75()
    try:
        _persist_m4_71_receipt(session, "a" * 64)
        first_snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = HistoricalM472VerificationReceiptM475Repository(session)
        first_receipt = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=first_snapshot.id, recorded_by="ministry")
        first_result = repository.record(
            verification_receipt_id=first_receipt.id,
            recorded_by="ministry",
        )

        _persist_m4_71_receipt(session, "b" * 64)
        second_snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        second_receipt = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        ).record(snapshot_id=second_snapshot.id, recorded_by="ministry")
        second_result = repository.record(
            verification_receipt_id=second_receipt.id,
            recorded_by="ministry",
        )

        page, has_more = repository.list(limit=1)
        assert has_more is True
        assert page[0].id == second_result.id

        next_page, next_has_more = repository.list(
            before_created_at=page[0].created_at,
            before_id=page[0].id,
            limit=1,
        )
        assert next_has_more is False
        assert next_page[0].id == first_result.id

        with pytest.raises(
            HistoricalM472VerificationReceiptM475PersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalM472VerificationReceiptM475PersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_76_detects_tampered_result() -> None:
    engine, session = _session_m4_75()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        repository = HistoricalM472VerificationReceiptM475Repository(session)
        record = repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        record.blockers_json = '[ "TAMPERED" ]'
        session.flush()
        with pytest.raises(
            HistoricalM472VerificationReceiptM475PersistenceError,
            match="structurally invalid|differs from reconstruction",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_76_missing_source_fails_closed() -> None:
    engine, session = _session_m4_75()
    try:
        _, receipt = _persist_m4_74_receipt(session)
        repository = HistoricalM472VerificationReceiptM475Repository(session)
        session.delete(receipt)
        session.flush()
        with pytest.raises(
            HistoricalM472VerificationReceiptM475PersistenceError,
            match="M4.74 independent verification receipt not found",
        ):
            repository.record(
                verification_receipt_id=receipt.id,
                recorded_by="ministry",
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_76_openapi_routes_are_registered() -> None:
    from morva.api.app import app

    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-72-verification-history-integrity-snapshots/"
        "independent-verification-receipt-history"
    )
    paths = app.openapi()["paths"]
    assert "post" in paths[prefix + "/{verification_receipt_id}"]
    assert "get" in paths[prefix]
    assert "get" in paths[prefix + "/{verification_id}/verify"]
