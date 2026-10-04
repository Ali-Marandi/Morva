from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect

import morva.persistence.database as database
from morva.api.app import app
from morva.persistence.database import init_db
from morva.persistence.historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM474VerificationReceiptHistoryIntegrityRecord,
    HistoricalM474VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.historical_m4_71_verification_history_integrity_m4_72 import (
    HistoricalM471VerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
)
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope
from tests.test_historical_m4_71_verification_history_integrity_m4_72 import (
    _persist_m4_71_receipt,
)
from tests.test_independent_historical_m4_72_verification_receipts_m4_74 import (
    _session_m4_74,
)


def _session_m4_75():
    engine, session = _session_m4_74()
    HistoricalM474VerificationReceiptHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_74_receipt(session, source_hash: str = "a" * 64):
    _persist_m4_71_receipt(session, source_hash)
    snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
        captured_by="ministry"
    )
    return IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(session).record(
        snapshot_id=snapshot.id,
        recorded_by="ministry",
    )


def test_m4_75_local_schema_registers_history_snapshot_model(monkeypatch) -> None:
    engine = create_engine("sqlite://", future=True)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "ENVIRONMENT", "test")
    try:
        database.init_db()
        assert inspect(engine).has_table(
            "historical_m4_74_verification_receipt_history_integrity_m4_75"
        )
    finally:
        engine.dispose()


def test_m4_75_captures_and_reverifies_m4_74_history() -> None:
    engine, session = _session_m4_75()
    try:
        _persist_m4_74_receipt(session)
        repository = HistoricalM474VerificationReceiptHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        assert snapshot.to_integrity().record_count == 1
        assert snapshot.to_integrity().valid_count == 1
        assert repository.verify(snapshot.id).id == snapshot.id
        assert repository.capture(captured_by="ministry").id == snapshot.id
    finally:
        session.close()
        engine.dispose()


def test_m4_75_rejects_second_actor_for_same_fingerprint() -> None:
    engine, session = _session_m4_75()
    try:
        _persist_m4_74_receipt(session)
        repository = HistoricalM474VerificationReceiptHistoryIntegrityRepository(session)
        repository.capture(captured_by="ministry")
        with pytest.raises(
            HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError,
            match="different actor",
        ):
            repository.capture(captured_by="auditor")
    finally:
        session.close()
        engine.dispose()


def test_m4_75_cursor_history_and_invalid_cursor() -> None:
    engine, session = _session_m4_75()
    try:
        _persist_m4_74_receipt(session, "a" * 64)
        repository = HistoricalM474VerificationReceiptHistoryIntegrityRepository(session)
        first = repository.capture(captured_by="ministry")

        _persist_m4_74_receipt(session, "b" * 64)
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
        assert next_page[0].id == first.id

        with pytest.raises(
            HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_75_detects_tampered_source_receipt() -> None:
    engine, session = _session_m4_75()
    try:
        receipt = _persist_m4_74_receipt(session)
        repository = HistoricalM474VerificationReceiptHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        receipt.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError,
            match="M4.74 history reconstruction failed",
        ):
            repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_75_detects_tampered_snapshot() -> None:
    engine, session = _session_m4_75()
    try:
        _persist_m4_74_receipt(session)
        repository = HistoricalM474VerificationReceiptHistoryIntegrityRepository(session)
        snapshot = repository.capture(captured_by="ministry")
        snapshot.fingerprint = "not-a-sha"
        session.flush()
        with pytest.raises(
            HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError,
            match="structurally invalid",
        ):
            repository.verify(snapshot.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_75_openapi_routes_are_registered() -> None:
    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-74-verification-receipt-history-integrity-snapshots"
    )
    paths = app.openapi()["paths"]
    assert "post" in paths[prefix]
    assert "get" in paths[prefix]
    assert "get" in paths[prefix + "/{snapshot_id}/verify"]


def _principal(scope: Scope) -> Principal:
    return Principal(
        user_id="m4-75-test",
        role="admin",
        scope=scope,
        scope_id="test",
        mfa_verified=True,
    )


def test_m4_75_snapshot_api_requires_authentication(monkeypatch) -> None:
    previous_override = app.dependency_overrides.pop(get_current_principal, None)
    monkeypatch.setattr(database, "ENVIRONMENT", "test")
    init_db()
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-74-verification-receipt-history-integrity-snapshots"
        )
        assert response.status_code == 401
    finally:
        if previous_override is not None:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_75_snapshot_api_enforces_ministry_scope() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.SCHOOL)
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-74-verification-receipt-history-integrity-snapshots"
        )
        assert response.status_code == 403
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_75_snapshot_api_returns_404_for_unknown_snapshot(monkeypatch) -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.MINISTRY)
    monkeypatch.setattr(database, "ENVIRONMENT", "test")
    init_db()
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-74-verification-receipt-history-integrity-snapshots/"
            f"{uuid4()}/verify"
        )
        assert response.status_code == 404
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override
