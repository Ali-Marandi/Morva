from __future__ import annotations

from datetime import timedelta

import pytest

from morva.persistence.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    HistoricalSnapshotFreshnessReceiptLineagePersistenceError,
    HistoricalSnapshotFreshnessReceiptLineageRepository,
)
from morva.api.app import app

from tests.test_historical_snapshot_freshness_receipt_lineage_m4_41 import (
    NOW,
    _session,
    _source_records,
)


def test_m4_42_history_is_newest_first_and_cursor_paginated():
    engine, session = _session()
    try:
        _, binding_one, receipt_one = _source_records(
            session,
            convergence_fingerprint="b" * 64,
        )
        _, binding_two, receipt_two = _source_records(
            session,
            convergence_fingerprint="c" * 64,
        )
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        first = repository.bind(
            freshness_receipt_id=receipt_one.id,
            historical_binding_id=binding_one.id,
            bound_by="ministry",
        )
        second = repository.bind(
            freshness_receipt_id=receipt_two.id,
            historical_binding_id=binding_two.id,
            bound_by="ministry",
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
        assert [record.id for record in next_page] == [first.id]
    finally:
        session.close()
        engine.dispose()


def test_m4_42_history_filters_exact_source_ids():
    engine, session = _session()
    try:
        _, binding_one, receipt_one = _source_records(
            session,
            convergence_fingerprint="b" * 64,
        )
        _, binding_two, receipt_two = _source_records(
            session,
            convergence_fingerprint="c" * 64,
        )
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        first = repository.bind(
            freshness_receipt_id=receipt_one.id,
            historical_binding_id=binding_one.id,
            bound_by="ministry",
        )
        repository.bind(
            freshness_receipt_id=receipt_two.id,
            historical_binding_id=binding_two.id,
            bound_by="ministry",
        )

        by_receipt, _ = repository.list(
            freshness_receipt_id=receipt_one.id,
        )
        assert [record.id for record in by_receipt] == [first.id]

        by_binding, _ = repository.list(
            historical_binding_id=binding_two.id,
        )
        assert len(by_binding) == 1
        assert by_binding[0].freshness_receipt_id == receipt_two.id

        by_snapshot, _ = repository.list(
            snapshot_id=first.snapshot_id,
        )
        assert len(by_snapshot) == 2
    finally:
        session.close()
        engine.dispose()


def test_m4_42_history_revalidates_and_fails_closed_on_tampering():
    engine, session = _session()
    try:
        _, binding, receipt = _source_records(
            session,
            convergence_fingerprint="b" * 64,
        )
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        lineage = repository.bind(
            freshness_receipt_id=receipt.id,
            historical_binding_id=binding.id,
            bound_by="ministry",
        )
        lineage.registry_fingerprint = "d" * 64
        session.flush()

        with pytest.raises(
            HistoricalSnapshotFreshnessReceiptLineagePersistenceError,
            match="lineage registry identity|fingerprint",
        ):
            repository.list(limit=10)
    finally:
        session.close()
        engine.dispose()


def test_m4_42_history_rejects_partial_cursor():
    engine, session = _session()
    try:
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        with pytest.raises(
            HistoricalSnapshotFreshnessReceiptLineagePersistenceError,
            match="limit must be between 1 and 100|before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=NOW, before_id=None, limit=0)
    finally:
        session.close()
        engine.dispose()


def test_m4_42_openapi_history_route_is_registered():
    paths = app.openapi()["paths"]
    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/history"
    )
    assert path in paths
    operation = paths[path]["get"]
    parameters = {parameter["name"] for parameter in operation["parameters"]}
    assert {
        "freshness_receipt_id",
        "historical_binding_id",
        "snapshot_id",
        "before_created_at",
        "before_id",
        "limit",
    } <= parameters
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"] == (
        "#/components/schemas/"
        "HistoricalSnapshotFreshnessReceiptLineageHistoryResponse"
    )
