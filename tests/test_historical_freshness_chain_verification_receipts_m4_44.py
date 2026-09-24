from __future__ import annotations

from datetime import timedelta

import pytest

from morva.api.app import app
from morva.persistence.historical_freshness_chain_verification_receipts_m4_44 import (
    HistoricalFreshnessChainVerificationReceiptPersistenceError,
    HistoricalFreshnessChainVerificationReceiptRecord,
    HistoricalFreshnessChainVerificationReceiptRepository,
)
from morva.persistence.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    HistoricalSnapshotFreshnessReceiptLineageRepository,
)

from morva.runtime.historical_freshness_chain_verifier_m4_43 import (
    verify_historical_freshness_chain,
)
from tests.test_historical_freshness_chain_verifier_m4_43 import _chain_inputs
from tests.test_historical_snapshot_freshness_receipt_lineage_m4_41 import (
    NOW,
    _session,
)


def _session_m4_44():
    engine, session = _session()
    HistoricalFreshnessChainVerificationReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _lineage_id(session, freshness_receipt_id):
    records, _ = HistoricalSnapshotFreshnessReceiptLineageRepository(session).list(
        freshness_receipt_id=freshness_receipt_id,
        limit=1,
    )
    assert len(records) == 1
    return records[0].id


def test_m4_44_records_and_reverifies_deterministic_chain_receipt():
    engine, session = _session_m4_44()
    try:
        inputs = _chain_inputs(session)
        verification = verify_historical_freshness_chain(**inputs)
        repository = HistoricalFreshnessChainVerificationReceiptRepository(session)
        lineage_id = _lineage_id(session, inputs["freshness_receipt_id"])

        record = repository.record(
            lineage_id=lineage_id,
            recorded_by="ministry",
        )
        assert record.to_verification().fingerprint == verification.fingerprint
        assert repository.verify(record.id).id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_44_history_is_cursor_paginated_and_reverified():
    engine, session = _session_m4_44()
    try:
        first_inputs = _chain_inputs(session)
        second_inputs = _chain_inputs(session)
        repository = HistoricalFreshnessChainVerificationReceiptRepository(session)
        first = repository.record(
            lineage_id=_lineage_id(session, first_inputs["freshness_receipt_id"]),
            recorded_by="ministry",
        )
        second = repository.record(
            lineage_id=_lineage_id(session, second_inputs["freshness_receipt_id"]),
            recorded_by="ministry",
        )
        first.created_at = NOW
        second.created_at = NOW + timedelta(minutes=1)
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


def test_m4_44_fails_closed_on_tampered_blockers():
    engine, session = _session_m4_44()
    try:
        inputs = _chain_inputs(session)
        repository = HistoricalFreshnessChainVerificationReceiptRepository(session)
        record = repository.record(
            lineage_id=_lineage_id(session, inputs["freshness_receipt_id"]),
            recorded_by="ministry",
        )
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            HistoricalFreshnessChainVerificationReceiptPersistenceError,
            match="persisted M4.44 verification receipt is structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_44_rejects_invalid_cursor_and_state():
    engine, session = _session_m4_44()
    try:
        repository = HistoricalFreshnessChainVerificationReceiptRepository(session)
        with pytest.raises(
            HistoricalFreshnessChainVerificationReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalFreshnessChainVerificationReceiptPersistenceError,
            match="state must be verified or blocked",
        ):
            repository.list(state="unknown")
        with pytest.raises(
            HistoricalFreshnessChainVerificationReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=NOW.replace(tzinfo=None))
    finally:
        session.close()
        engine.dispose()


def test_m4_44_openapi_routes_are_registered():
    paths = app.openapi()["paths"]
    write_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/{lineage_id}/verification-receipts"
    )
    history_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/verification-history"
    )
    assert write_path in paths
    assert history_path in paths
    assert "post" in paths[write_path]
    assert "get" in paths[history_path]
