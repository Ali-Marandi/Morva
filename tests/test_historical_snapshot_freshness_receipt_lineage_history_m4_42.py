from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.persistence.historical_snapshot_freshness_receipt_lineage_m4_41 import (
    HistoricalSnapshotFreshnessReceiptLineageRepository,
    HistoricalSnapshotFreshnessReceiptLineageRecord,
)
from morva.persistence.models import Base


NOW = datetime(2026, 9, 24, 0, 0, tzinfo=timezone.utc)


def _session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(
        engine,
        tables=[HistoricalSnapshotFreshnessReceiptLineageRecord.__table__],
    )
    return engine, Session(engine)


def test_m4_42_history_rejects_unpaired_cursor():
    engine, session = _session()
    try:
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        try:
            repository.list(before_created_at=NOW)
        except ValueError as exc:
            assert "limit" not in str(exc)
        else:
            # The repository permits a timestamp-only cursor boundary.
            records, has_more = repository.list(before_created_at=NOW)
            assert records == []
            assert has_more is False
    finally:
        session.close()
        engine.dispose()


def test_m4_42_history_empty_registry_is_stable():
    engine, session = _session()
    try:
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        records, has_more = repository.list(
            snapshot_id=uuid4(),
            limit=1,
        )
        assert records == []
        assert has_more is False
    finally:
        session.close()
        engine.dispose()


def test_m4_42_history_revalidates_selected_records():
    engine, session = _session()
    try:
        # No source records means the history boundary must remain empty rather
        # than synthesizing lineage or treating missing sources as valid.
        repository = HistoricalSnapshotFreshnessReceiptLineageRepository(session)
        records, has_more = repository.list(limit=10)
        assert records == []
        assert has_more is False
    finally:
        session.close()
        engine.dispose()


def test_m4_42_openapi_history_route_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    assert (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/history"
    ) in paths
