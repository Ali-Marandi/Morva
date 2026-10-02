from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import morva.api.v1.integration_execution_readiness as api_module
from morva.api.app import app
from morva.persistence.historical_m4_71_verification_history_integrity_m4_72 import (
    HistoricalM471VerificationHistoryIntegrityRecord,
    HistoricalM471VerificationHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
)
from morva.runtime.config import Settings
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope
from tests.test_historical_m4_71_verification_history_integrity_m4_72 import (
    _persist_m4_71_receipt,
    _session_m4_72,
)


def _session_m4_74():
    engine, session = _session_m4_72()
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def test_m4_74_records_and_reverifies_independent_result() -> None:
    engine, session = _session_m4_74()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert (
            repository.record(snapshot_id=snapshot.id, recorded_by="ministry").id
            == record.id
        )
    finally:
        session.close()
        engine.dispose()


def test_m4_74_rejects_second_actor_for_same_fingerprint() -> None:
    engine, session = _session_m4_74()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        with pytest.raises(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
            match="different actor",
        ):
            repository.record(snapshot_id=snapshot.id, recorded_by="auditor")
    finally:
        session.close()
        engine.dispose()


def test_m4_74_cursor_history_and_invalid_cursor() -> None:
    engine, session = _session_m4_74()
    try:
        _persist_m4_71_receipt(session, "a" * 64)
        first = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        first_receipt = repository.record(snapshot_id=first.id, recorded_by="ministry")

        _persist_m4_71_receipt(session, "b" * 64)
        second = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        second_receipt = repository.record(snapshot_id=second.id, recorded_by="ministry")

        page, has_more = repository.list(limit=1)
        assert has_more is True
        assert page[0].id == second_receipt.id

        next_page, next_has_more = repository.list(
            before_created_at=page[0].created_at,
            before_id=page[0].id,
            limit=1,
        )
        assert next_has_more is False
        assert next_page[0].id == first_receipt.id

        with pytest.raises(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
            match="limit must be between 1 and 100",
        ):
            repository.list(limit=0)
        with pytest.raises(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
            match="before_created_at must be timezone-aware",
        ):
            repository.list(before_created_at=datetime.now())
    finally:
        session.close()
        engine.dispose()


def test_m4_74_detects_tampered_receipt() -> None:
    engine, session = _session_m4_74()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        record = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
            match="structurally invalid|differs from reconstruction",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_74_invalid_snapshot_fails_closed() -> None:
    engine, session = _session_m4_74()
    try:
        _persist_m4_71_receipt(session)
        snapshot = HistoricalM471VerificationHistoryIntegrityRepository(session).capture(
            captured_by="ministry"
        )
        snapshot.fingerprint = "not-a-sha"
        session.flush()
        repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
            session
        )
        with pytest.raises(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
            match="source snapshot is structurally invalid",
        ):
            repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
    finally:
        session.close()
        engine.dispose()


def test_m4_74_openapi_routes_are_registered() -> None:
    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-72-verification-history-integrity-snapshots"
    )
    paths = app.openapi()["paths"]
    assert "post" in paths[prefix + "/{snapshot_id}/verification-receipts"]
    assert "get" in paths[prefix + "/verification-history"]
    assert "get" in paths[prefix + "/verification-receipts/{verification_id}/verify"]


def _api_test_sessionmaker():
    engine = create_engine(
        "sqlite://",
        future=True,
        connect_args={"check_same_thread": False},
    )
    HistoricalM471VerificationHistoryIntegrityRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )


def _principal(scope: Scope) -> Principal:
    return Principal(
        user_id="m4-74-test",
        role="admin",
        scope=scope,
        scope_id="test",
        mfa_verified=True,
    )


def test_m4_74_verification_receipt_api_requires_authentication(monkeypatch) -> None:
    previous_override = app.dependency_overrides.pop(get_current_principal, None)
    try:
        import morva.security.auth as auth_module

        monkeypatch.setattr(
            auth_module,
            "settings",
            Settings(environment="test"),
        )
        response = TestClient(app).get(
            (
                "/api/v1/integration-execution/readiness/convergence/freshness/"
                "policy-registry-snapshot-bound/receipt-lineage/"
                "independent-verification-history-integrity/"
                "m4-72-verification-history-integrity-snapshots/verification-history"
            )
        )
        assert response.status_code == 401
    finally:
        if previous_override is not None:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_74_verification_receipt_api_rejects_invalid_uuid() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.MINISTRY)
    try:
        response = TestClient(app).post(
            (
                "/api/v1/integration-execution/readiness/convergence/freshness/"
                "policy-registry-snapshot-bound/receipt-lineage/"
                "independent-verification-history-integrity/"
                "m4-72-verification-history-integrity-snapshots/"
                "not-a-uuid/verification-receipts"
            )
        )
        assert response.status_code == 422
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_74_verification_receipt_api_enforces_ministry_scope() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.SCHOOL)
    try:
        response = TestClient(app).get(
            (
                "/api/v1/integration-execution/readiness/convergence/freshness/"
                "policy-registry-snapshot-bound/receipt-lineage/"
                "independent-verification-history-integrity/"
                "m4-72-verification-history-integrity-snapshots/verification-history"
            )
        )
        assert response.status_code == 403
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_74_verification_receipt_api_returns_404_for_unknown_snapshot(monkeypatch) -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.MINISTRY)
    engine, testing_sessionmaker = _api_test_sessionmaker()
    monkeypatch.setattr(api_module, "SessionLocal", testing_sessionmaker)
    try:
        response = TestClient(app).post(
            (
                "/api/v1/integration-execution/readiness/convergence/freshness/"
                "policy-registry-snapshot-bound/receipt-lineage/"
                "independent-verification-history-integrity/"
                "m4-72-verification-history-integrity-snapshots/"
                f"{uuid4()}/verification-receipts"
            )
        )
        assert response.status_code == 404
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override
        engine.dispose()


def test_m4_74_verification_receipt_api_returns_404_for_unknown_receipt(monkeypatch) -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.MINISTRY)
    engine, testing_sessionmaker = _api_test_sessionmaker()
    monkeypatch.setattr(api_module, "SessionLocal", testing_sessionmaker)
    try:
        response = TestClient(app).get(
            (
                "/api/v1/integration-execution/readiness/convergence/freshness/"
                "policy-registry-snapshot-bound/receipt-lineage/"
                "independent-verification-history-integrity/"
                "m4-72-verification-history-integrity-snapshots/"
                "verification-receipts/"
                f"{uuid4()}/verify"
            )
        )
        assert response.status_code == 404
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override
        engine.dispose()
