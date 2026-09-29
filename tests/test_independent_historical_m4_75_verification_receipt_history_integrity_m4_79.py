from __future__ import annotations

from sqlalchemy import select
import pytest

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475Repository,
)
from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_75_verification_receipt_history_integrity_m4_79 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from tests.test_independent_historical_m4_72_verification_receipt_m4_75 import (
    _persist_m4_74_receipt,
)
from tests.test_independent_historical_m4_75_verification_receipt_history_integrity_m4_78 import (
    _session_m4_78,
)


def _source_records(session):
    from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
        HistoricalM472VerificationReceiptM475Record,
    )

    return list(
        session.scalars(
            select(HistoricalM472VerificationReceiptM475Record).order_by(
                HistoricalM472VerificationReceiptM475Record.created_at.asc(),
                HistoricalM472VerificationReceiptM475Record.id.asc(),
            )
        )
    )


def _persist_m4_77_snapshot(session):
    _, receipt = _persist_m4_74_receipt(session)
    HistoricalM472VerificationReceiptM475Repository(session).record(
        verification_receipt_id=receipt.id,
        recorded_by="ministry",
    )
    return HistoricalM475VerificationReceiptHistoryIntegrityRepository(session).capture(
        captured_by="ministry"
    )


def _persist_m4_79_result(session, actor="ministry"):
    snapshot = _persist_m4_77_snapshot(session)
    repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
        session
    )
    record = repository.record(snapshot_id=snapshot.id, recorded_by=actor)
    session.commit()
    return repository, snapshot, record


def test_m4_79_persists_and_reverifies_m4_78_result() -> None:
    engine, session = _session_m4_78()
    try:
        IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord.__table__.create(
            bind=engine,
            checkfirst=True,
        )
        repository, snapshot, record = _persist_m4_79_result(session)
        assert record.snapshot_id == snapshot.id
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_79_is_fingerprint_idempotent() -> None:
    engine, session = _session_m4_78()
    try:
        IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord.__table__.create(
            bind=engine,
            checkfirst=True,
        )
        snapshot = _persist_m4_77_snapshot(session)
        repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        )
        first = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        second = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert second.id == first.id
    finally:
        session.close()
        engine.dispose()


def test_m4_79_cursor_history() -> None:
    engine, session = _session_m4_78()
    try:
        IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord.__table__.create(
            bind=engine,
            checkfirst=True,
        )
        repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        )
        first_snapshot = _persist_m4_77_snapshot(session)
        first = repository.record(snapshot_id=first_snapshot.id, recorded_by="ministry")

        second_snapshot = _persist_m4_77_snapshot(session)
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
        assert next_page[0].id == first.id
    finally:
        session.close()
        engine.dispose()


def test_m4_79_detects_tampered_persisted_result() -> None:
    engine, session = _session_m4_78()
    try:
        IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord.__table__.create(
            bind=engine,
            checkfirst=True,
        )
        repository, _, record = _persist_m4_79_result(session)
        record.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
            match="persisted M4.79 independent verification result is structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_79_detects_tampered_source_history() -> None:
    engine, session = _session_m4_78()
    try:
        IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord.__table__.create(
            bind=engine,
            checkfirst=True,
        )
        repository, _, record = _persist_m4_79_result(session)
        source = _source_records(session)[0]
        source.recorded_by = "tampered-source-actor"
        session.flush()
        with pytest.raises(
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
            match="M4.79 independent verification result differs from reconstruction",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_79_openapi_routes_are_registered() -> None:
    from morva.api.app import app

    paths = app.openapi()["paths"]
    assert (
        "post"
        in paths[
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-76-verification-receipt-history-integrity-snapshots/"
            "{snapshot_id}/verification-receipts"
        ]
    )
    assert (
        "get"
        in paths[
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-76-verification-receipt-history-integrity-snapshots/"
            "verification-receipts"
        ]
    )
    assert (
        "get"
        in paths[
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-76-verification-receipt-history-integrity-snapshots/"
            "verification-receipts/{verification_id}/verify"
        ]
    )
