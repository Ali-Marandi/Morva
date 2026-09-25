from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from morva.persistence.historical_freshness_chain_verification_receipts_m4_44 import (
    HistoricalFreshnessChainVerificationReceiptRepository,
)
from morva.persistence.historical_freshness_verification_history_integrity_m4_47 import (
    HistoricalFreshnessVerificationHistoryIntegrityRecord,
    HistoricalFreshnessVerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_freshness_receipt_verifications_m4_46 import (
    IndependentHistoricalFreshnessReceiptVerificationRecord,
    IndependentHistoricalFreshnessReceiptVerificationRepository,
)
from morva.persistence.independent_historical_freshness_verification_history_integrity_receipts_m4_49 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository,
)
from tests.test_historical_freshness_chain_verifier_m4_43 import _chain_inputs
from tests.test_historical_freshness_chain_verification_receipts_m4_44 import _session_m4_44
from tests.test_independent_historical_freshness_chain_verification_receipt_m4_45 import (
    _lineage_id,
)


def _session_m4_49():
    engine, session = _session_m4_44()
    IndependentHistoricalFreshnessReceiptVerificationRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    HistoricalFreshnessVerificationHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_snapshot(session, convergence_fingerprint: str = "a" * 64):
    inputs = _chain_inputs(session, convergence_fingerprint=convergence_fingerprint)
    source = HistoricalFreshnessChainVerificationReceiptRepository(session).record(
        lineage_id=_lineage_id(session, inputs["freshness_receipt_id"]),
        recorded_by="ministry",
    )
    IndependentHistoricalFreshnessReceiptVerificationRepository(session).record(
        receipt_id=source.id,
        recorded_by="ministry",
    )
    return HistoricalFreshnessVerificationHistoryIntegrityRepository(session).capture(
        captured_by="ministry"
    )


def test_m4_49_records_and_reverifies_independent_m4_48_result():
    engine, session = _session_m4_49()
    try:
        snapshot = _persist_snapshot(session)
        repository = IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(snapshot_id=snapshot.id, recorded_by="ministry").id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_49_is_cursor_paginated_and_reverified():
    engine, session = _session_m4_49()
    try:
        first_snapshot = _persist_snapshot(session, "a" * 64)
        second_snapshot = _persist_snapshot(session, "b" * 64)
        repository = IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
            session
        )
        first = repository.record(snapshot_id=first_snapshot.id, recorded_by="ministry")
        second = repository.record(snapshot_id=second_snapshot.id, recorded_by="ministry")
        first.created_at = first.created_at.replace(second=0)
        second.created_at = first.created_at + timedelta(minutes=1)
        session.flush()

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


def test_m4_49_preserves_snapshot_point_in_time_boundary():
    engine, session = _session_m4_49()
    try:
        snapshot = _persist_snapshot(session, "a" * 64)
        _persist_snapshot(session, "b" * 64)
        repository = IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
            session
        )
        receipt = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert repository.verify(receipt.id).id == receipt.id
    finally:
        session.close()
        engine.dispose()


def test_m4_49_fails_closed_on_tampered_blockers():
    engine, session = _session_m4_49()
    try:
        snapshot = _persist_snapshot(session)
        repository = IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
            match="persisted M4.49 independent verification receipt is structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_49_rejects_invalid_cursor():
    engine, session = _session_m4_49()
    try:
        repository = IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRepository(
            session
        )
        with pytest.raises(
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_49_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    write_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/snapshots/{snapshot_id}/verification-receipts"
    )
    history_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/verification-history"
    )
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "verification-receipts/{verification_receipt_id}/verify"
    )
    assert "post" in paths[write_path]
    assert "get" in paths[history_path]
    assert "get" in paths[verify_path]
