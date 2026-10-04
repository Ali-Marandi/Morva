from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect, select

import morva.persistence.database as database
import morva.security.auth as auth_module
from morva.api.app import app
from morva.persistence.database import init_db
from morva.persistence.historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    HistoricalM474VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
)
from morva.persistence.independent_historical_m4_75_verification_receipts_m4_77 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from morva.runtime.config import Settings
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope
from tests.test_historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    _persist_m4_74_receipt,
    _session_m4_75,
)


def _session_m4_77():
    engine, session = _session_m4_77()
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _persist_m4_75_snapshot(session, source_hash: str = "a" * 64):
    _persist_m4_74_receipt(session, source_hash)
    return HistoricalM474VerificationReceiptHistoryIntegrityRepository(session).capture(
        captured_by="ministry"
    )


def _principal(scope: Scope) -> Principal:
    return Principal(
        user_id="m4-77-test",
        role="admin",
        scope=scope,
        scope_id="test",
        mfa_verified=True,
    )


def test_m4_77_local_schema_registers_persistence_model(monkeypatch) -> None:
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
        repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
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
        repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        )
        repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        with pytest.raises(
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
            match="different actor",
        ):
            repository.record(snapshot_id=snapshot.id, recorded_by="auditor")
    finally:
        session.close()
        engine.dispose()


def test_m4_77_cursor_history_and_filters() -> None:
    engine, session = _session_m4_77()
    try:
        first_snapshot = _persist_m4_75_snapshot(session, "a" * 64)
        first_record = (
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(session)
            .record(snapshot_id=first_snapshot.id, recorded_by="ministry")
        )
        second_snapshot = _persist_m4_75_snapshot(session, "b" * 64)
        repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        )
        second_record = repository.record(
            snapshot_id=second_snapshot.id, recorded_by="ministry"
        )

        page, has_more = repository.list(limit=1)
        assert has_more is True
        assert page[0].id == second_record.id

        next_page, next_has_more = repository.list(
            before_created_at=page[0].created_at,
            before_id=page[0].id,
            limit=1,
        )
        assert next_has_more is False
        assert next_page[0].id == first_record.id

        valid_page, valid_more = repository.list(
            snapshot_id=first_snapshot.id,
            valid=True,
            limit=10,
        )
        assert valid_more is False
        assert [item.id for item in valid_page] == [first_record.id]
    finally:
        session.close()
        engine.dispose()


def test_m4_77_detects_tampered_source_receipt() -> None:
    engine, session = _session_m4_77()
    try:
        snapshot = _persist_m4_75_snapshot(session)
        record = (
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(session)
            .record(snapshot_id=snapshot.id, recorded_by="ministry")
        )
        source = session.scalar(
            select(IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord)
        )
        source.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
            match="M4.76 independent reconstruction failed",
        ):
            repository = (
                IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
                    session
                )
            )
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_77_detects_tampered_persisted_receipt() -> None:
    engine, session = _session_m4_77()
    try:
        snapshot = _persist_m4_75_snapshot(session)
        repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        record.verification_fingerprint = "not-a-sha"
        session.flush()
        with pytest.raises(
            IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
            match="structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_77_openapi_routes_are_registered() -> None:
    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-75-verification-receipt-history-integrity-snapshots"
    )
    paths = app.openapi()["paths"]
    assert "post" in paths[prefix + "/{snapshot_id}/verification-receipts"]
    assert "get" in paths[prefix + "/verification-history"]
    assert "get" in paths[prefix + "/verification-receipts/{verification_id}/verify"]


def test_m4_77_receipt_api_requires_authentication(monkeypatch) -> None:
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
                "m4-75-verification-receipt-history-integrity-snapshots/verification-history"
            )
        assert response.status_code == 401
    finally:
        if previous_override is not None:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_77_receipt_api_enforces_ministry_scope() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.SCHOOL)
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-75-verification-receipt-history-integrity-snapshots/verification-history"
        )
        assert response.status_code == 403
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_77_unknown_receipt_returns_404() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.MINISTRY)
    init_db()
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-75-verification-receipt-history-integrity-snapshots/"
            f"verification-receipts/{uuid4()}/verify"
        )
        assert response.status_code == 404
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override
