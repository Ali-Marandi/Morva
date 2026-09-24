from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from morva.persistence.independent_historical_freshness_receipt_verifications_m4_46 import (
    IndependentHistoricalFreshnessReceiptVerificationPersistenceError,
    IndependentHistoricalFreshnessReceiptVerificationRecord,
    IndependentHistoricalFreshnessReceiptVerificationRepository,
)
from morva.persistence.historical_freshness_chain_verification_receipts_m4_44 import (
    HistoricalFreshnessChainVerificationReceiptRepository,
)
from morva.persistence.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    HistoricalSnapshotFreshnessReceiptLineageRepository,
)
from morva.runtime.historical_freshness_chain_verifier_m4_43 import (
    verify_historical_freshness_chain,
)
from tests.test_historical_freshness_chain_verifier_m4_43 import _chain_inputs
from tests.test_historical_freshness_chain_verification_receipts_m4_44 import _session_m4_44
from tests.test_independent_historical_freshness_chain_verification_receipt_m4_45 import (
    _lineage_id,
)


def _session_m4_46():
    engine, session = _session_m4_44()
    IndependentHistoricalFreshnessReceiptVerificationRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def test_m4_46_records_and_reverifies_independent_receipt():
    engine, session = _session_m4_46()
    try:
        inputs = _chain_inputs(session)
        source = HistoricalFreshnessChainVerificationReceiptRepository(session).record(
            lineage_id=_lineage_id(session, inputs["freshness_receipt_id"]),
            recorded_by="ministry",
        )
        repository = IndependentHistoricalFreshnessReceiptVerificationRepository(session)
        record = repository.record(receipt_id=source.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_46_is_cursor_paginated_and_reverified():
    engine, session = _session_m4_46()
    try:
        first_inputs = _chain_inputs(session)
        second_inputs = _chain_inputs(session)
        source_repository = HistoricalFreshnessChainVerificationReceiptRepository(session)
        repository = IndependentHistoricalFreshnessReceiptVerificationRepository(session)
        first_source = source_repository.record(
            lineage_id=_lineage_id(session, first_inputs["freshness_receipt_id"]),
            recorded_by="ministry",
        )
        second_source = source_repository.record(
            lineage_id=_lineage_id(session, second_inputs["freshness_receipt_id"]),
            recorded_by="ministry",
        )
        first = repository.record(receipt_id=first_source.id, recorded_by="ministry")
        second = repository.record(receipt_id=second_source.id, recorded_by="ministry")
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


def test_m4_46_fails_closed_on_tampered_blockers():
    engine, session = _session_m4_46()
    try:
        inputs = _chain_inputs(session)
        source = HistoricalFreshnessChainVerificationReceiptRepository(session).record(
            lineage_id=_lineage_id(session, inputs["freshness_receipt_id"]),
            recorded_by="ministry",
        )
        repository = IndependentHistoricalFreshnessReceiptVerificationRepository(session)
        record = repository.record(receipt_id=source.id, recorded_by="ministry")
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalFreshnessReceiptVerificationPersistenceError,
            match="persisted M4.46 independent verification receipt is structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_46_rejects_invalid_cursor():
    engine, session = _session_m4_46()
    try:
        repository = IndependentHistoricalFreshnessReceiptVerificationRepository(session)
        with pytest.raises(
            IndependentHistoricalFreshnessReceiptVerificationPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalFreshnessReceiptVerificationPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_46_openapi_routes_are_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    write_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "verification-receipts/{receipt_id}/independent-verification-receipts"
    )
    history_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/independent-verification-history"
    )
    verify_path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-receipts/{verification_receipt_id}/verify"
    )
    assert "post" in paths[write_path]
    assert "get" in paths[history_path]
    assert "get" in paths[verify_path]
