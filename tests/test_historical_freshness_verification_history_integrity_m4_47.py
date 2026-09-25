from __future__ import annotations

from datetime import datetime

import pytest

from morva.persistence.historical_freshness_chain_verification_receipts_m4_44 import (
    HistoricalFreshnessChainVerificationReceiptRepository,
)
from morva.persistence.historical_freshness_verification_history_integrity_m4_47 import (
    HistoricalFreshnessVerificationHistoryIntegrityPersistenceError,
    HistoricalFreshnessVerificationHistoryIntegrityRecord,
    HistoricalFreshnessVerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_freshness_receipt_verifications_m4_46 import (
    IndependentHistoricalFreshnessReceiptVerificationRepository,
)
from tests.test_historical_freshness_chain_verifier_m4_43 import _chain_inputs
from tests.test_historical_freshness_chain_verification_receipts_m4_44 import _session_m4_44
from tests.test_independent_historical_freshness_chain_verification_receipt_m4_45 import (
    _lineage_id,
)


def _session_m4_47():
    engine, session = _session_m4_44()
    IndependentHistoricalFreshnessVerificationRecord = (
        __import__(
            "morva.persistence.independent_historical_freshness_receipt_verifications_m4_46",
            fromlist=["IndependentHistoricalFreshnessReceiptVerificationRecord"],
        ).IndependentHistoricalFreshnessReceiptVerificationRecord
    )
    IndependentHistoricalFreshnessVerificationRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    HistoricalFreshnessVerificationHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_source_verification(session, convergence_fingerprint: str = "a" * 64):
    inputs = _chain_inputs(
        session,
        convergence_fingerprint=convergence_fingerprint,
    )
    source = HistoricalFreshnessChainVerificationReceiptRepository(session).record(
        lineage_id=_lineage_id(session, inputs["freshness_receipt_id"]),
        recorded_by="ministry",
    )
    return IndependentHistoricalFreshnessReceiptVerificationRepository(session).record(
        receipt_id=source.id,
        recorded_by="ministry",
    )


def test_m4_47_captures_and_reverifies_history_integrity():
    engine, session = _session_m4_47()
    try:
        source = _persist_source_verification(session)
        repository = HistoricalFreshnessVerificationHistoryIntegrityRepository(session)
        record = repository.capture(captured_by="ministry")
        integrity = record.to_integrity()
        assert integrity.record_count == 1
        assert integrity.valid_count == 1
        assert integrity.chain_valid_count == 1
        assert integrity.history_fingerprint
        assert repository.verify(record.id).id == record.id
        assert repository.capture(captured_by="ministry").id == record.id
        assert source.id
    finally:
        session.close()
        engine.dispose()


def test_m4_47_preserves_point_in_time_snapshot_after_history_append():
    engine, session = _session_m4_47()
    try:
        _persist_source_verification(session, "a" * 64)
        repository = HistoricalFreshnessVerificationHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        _persist_source_verification(session, "b" * 64)

        assert repository.verify(snapshot.id).id == snapshot.id
        current = repository.capture(captured_by="ministry")
        assert current.to_integrity().record_count == 2
    finally:
        session.close()
        engine.dispose()


def test_m4_47_detects_tampered_source_record():
    engine, session = _session_m4_47()
    try:
        _persist_source_verification(session)
        snapshot_repository = HistoricalFreshnessVerificationHistoryIntegrityRepository(
            session
        )
        snapshot = snapshot_repository.capture(captured_by="ministry")
        source_repository = IndependentHistoricalFreshnessReceiptVerificationRepository(
            session
        )
        record = source_repository.list(limit=1)[0][0]
        record.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            HistoricalFreshnessVerificationHistoryIntegrityPersistenceError,
            match="M4.46 history reconstruction failed",
        ):
            snapshot_repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_47_is_cursor_paginated():
    engine, session = _session_m4_47()
    try:
        _persist_source_verification(session, "a" * 64)
        repository = HistoricalFreshnessVerificationHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")

        _persist_source_verification(session, "b" * 64)
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


def test_m4_47_rejects_invalid_cursor():
    engine, session = _session_m4_47()
    try:
        repository = HistoricalFreshnessVerificationHistoryIntegrityRepository(session)
        with pytest.raises(
            HistoricalFreshnessVerificationHistoryIntegrityPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalFreshnessVerificationHistoryIntegrityPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_47_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    write_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/snapshots"
    )
    history_path = write_path
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/snapshots/{snapshot_id}/verify"
    )
    assert "post" in paths[write_path]
    assert "get" in paths[history_path]
    assert "get" in paths[verify_path]
