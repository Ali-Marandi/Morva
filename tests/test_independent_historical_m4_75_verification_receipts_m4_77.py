from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect

import morva.persistence.database as database
import morva.security.auth as auth_module
from morva.api.app import app
from morva.persistence.database import init_db
from morva.persistence.historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    HistoricalM474VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_75_verification_receipts_m4_77 import (
    IndependentHistoricalM475VerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM475VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM475VerificationHistoryIntegrityReceiptRepository,
)
from morva.runtime.config import Settings
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope
from tests.test_historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    _persist_m4_74_receipt,
    _session_m4_75,
)


def _session_m4_77():
    engine, session = _session_m4_75()
    IndependentHistoricalM475VerificationHistoryIntegrityReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_75_snapshot(session, source_hash: str = "a" * 64):
    _persist_m4_74_receipt(session, source_hash)
    return HistoricalM474VerificationReceiptHistoryIntegrityRepository(session).capture(
        captured_by="ministry"
    )


def test_m4_77_local_schema_registers_verification_receipt_model(monkeypatch) -> None:
    engine = create_engine("sqlite://", future=True)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "ENVIRONMENT", "test")
    try:
        database.init_db()
        assert inspect(engine).has_table(
            "independent_historical_m4_75_verification_receipts_m4_77"
        )
    finally:
        engine.dispose()


def test_m4_77_records_and_reverifies_m4_76_result() -> None:
    engine, session = _session_m4_77()
    try:
        snapshot = _persist_m4_75_snapshot(session)
        repository = IndependentHistoricalM475VerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert repository.record(snapshot_id=snapshot.id, recorded_by="ministry").id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_77_rejects_second_actor_for_same_fingerprint() -> None:
    engine, session = _session_m4_77()
    try:
        snapshot = _persist_m4_75_snapshot(session)
        repository = IndependentHistoricalM475VerificationHistoryIntegrityReceiptRepository(
            session
        )
        repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        with pytest.raises(
            IndependentHistoricalM475VerificationHistoryIntegrityReceiptPersistenceError,
            match="different actor",
        ):
            repository.record(snapshot_id=snapshot.id, recorded_by="auditor")
    finally:
        session.close()
        engine.dispose()


def test_m4_77_cursor_history_and_invalid_cursor() -> None:
    engine, session = _session_m4_77()
    try:
        repository = IndependentHistoricalM475VerificationHistoryIntegrityReceiptRepository(
            session
        )
        first_snapshot = _persist_m4_75_snapshot(session, "a" * 64)
        first = repository.record(snapshot_id=first_snapshot.id, recorded_by="ministry")
        second_snapshot = _persist_m4_75_snapshot(session, "b" * 64)
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

        with pytest.raises(
            IndependentHistoricalM475VerificationHistoryIntegrityReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalM475VerificationHistoryIntegrityReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_77_detects_tampered_source_receipt() -> None:
    engine, session = _session_m4_77()
    try:
        source = _persist_m4_74_receipt(session)
        snapshot = HistoricalM474VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        repository = IndependentHistoricalM475VerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        source.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM475VerificationHistoryIntegrityReceiptPersistenceError,
            match="M4.76 independent reconstruction failed",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_77_detects_tampered_persisted_receipt() -> None:
    engine, session = _session_m4_77()
    try:
        snapshot = _persist_m4_75_snapshot(session)
        repository = IndependentHistoricalM475VerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM475VerificationHistoryIntegrityReceiptPersistenceError,
            match="persisted M4.77 blockers payload is invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_77_openapi_routes_are_registered() -> None:
    paths = app.openapi()["paths"]
    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-75-verification-receipt-history-integrity-snapshots"
    )
    assert "post" in paths[prefix + "/{snapshot_id}/verification-receipts"]
    assert "get" in paths[prefix + "/{snapshot_id}/verification-receipts"]
    assert "get" in paths[
        prefix + "/{snapshot_id}/verification-receipts/{verification_receipt_id}/verify"
    ]


def test_m4_77_persistence_api_requires_authentication(monkeypatch) -> None:
    previous_override = app.dependency_overrides.pop(get_current_principal, None)
    monkeypatch.setattr(database, "ENVIRONMENT", "test")
    monkeypatch.setattr(auth_module, "settings", Settings(environment="test"))
    init_db()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/integration-execution/readiness/convergence/freshness/"
                "policy-registry-snapshot-bound/receipt-lineage/"
                "independent-verification-history-integrity/"
                "m4-75-verification-receipt-history-integrity-snapshots"
                "/verification-history"
            )
        assert response.status_code == 401
    finally:
        if previous_override is not None:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_77_persistence_api_returns_404_for_unknown_receipt() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="m4-77-test",
        role="admin",
        scope=Scope.MINISTRY,
        scope_id="test",
        mfa_verified=True,
    )
    init_db()
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/integration-execution/readiness/convergence/freshness/"
                "policy-registry-snapshot-bound/receipt-lineage/"
                "independent-verification-history-integrity/"
                "m4-75-verification-receipt-history-integrity-snapshots/"
                + str(uuid4())
                + "/verification-receipts/"
                + str(uuid4())
                + "/verify"
            )
        assert response.status_code == 404
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override
