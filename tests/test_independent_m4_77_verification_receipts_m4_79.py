from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect

import morva.api.v1.m4_79_verification_receipts as m4_79_api
import morva.persistence.database as database
from morva.api.app import app
from morva.persistence.database import init_db
import morva.security.auth as auth_module
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479PersistenceError,
    IndependentM477VerificationReceiptM479Record,
    IndependentM477VerificationReceiptM479Repository,
)
from morva.security.auth import get_current_principal
from morva.runtime.config import Settings
from morva.security.policy import Principal, Scope
from tests.test_independent_historical_m4_75_verification_receipt_m4_78 import (
    _persist_m4_77_receipt,
)
from tests.test_independent_historical_m4_75_verification_receipts_m4_77 import (
    _session_m4_77,
)


def _session_m4_79():
    engine, session = _session_m4_77()
    IndependentM477VerificationReceiptM479Record.__table__.create(
        bind=engine,
        checkfirst=True,
    )
    return engine, session


def _principal(scope: Scope) -> Principal:
    return Principal(
        user_id="m4-79-test",
        role="admin",
        scope=scope,
        scope_id="test",
        mfa_verified=True,
    )


def test_m4_79_local_schema_registers_persistence_model(monkeypatch) -> None:
    engine = create_engine("sqlite://", future=True)
    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database, "ENVIRONMENT", "test")
    try:
        database.init_db()
        assert inspect(engine).has_table(
            "independent_m4_77_verification_receipts_m4_79"
        )
    finally:
        engine.dispose()


def test_m4_79_records_and_reverifies_m4_78_result() -> None:
    engine, session = _session_m4_79()
    try:
        _, receipt, _, _ = _persist_m4_77_receipt(session)
        repository = IndependentM477VerificationReceiptM479Repository(session)
        record = repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        assert record.to_verification().valid is True
        assert repository.verify(record.id).id == record.id
        assert (
            repository.record(
                verification_receipt_id=receipt.id,
                recorded_by="ministry",
            ).id
            == record.id
        )
    finally:
        session.close()
        engine.dispose()


def test_m4_79_rejects_second_actor_for_same_fingerprint() -> None:
    engine, session = _session_m4_79()
    try:
        _, receipt, _, _ = _persist_m4_77_receipt(session)
        repository = IndependentM477VerificationReceiptM479Repository(session)
        repository.record(
            verification_receipt_id=receipt.id,
            recorded_by="ministry",
        )
        with pytest.raises(
            IndependentM477VerificationReceiptM479PersistenceError,
            match="different actor",
        ):
            repository.record(
                verification_receipt_id=receipt.id,
                recorded_by="auditor",
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_79_cursor_history_and_filter() -> None:
    engine, session = _session_m4_79()
    try:
        _, first_receipt, _, _ = _persist_m4_77_receipt(session)
        repository = IndependentM477VerificationReceiptM479Repository(session)
        first = repository.record(
            verification_receipt_id=first_receipt.id,
            recorded_by="ministry",
        )
        _, second_receipt, _, _ = _persist_m4_77_receipt(session, "b" * 64)
        second = repository.record(
            verification_receipt_id=second_receipt.id,
            recorded_by="ministry",
        )

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

        filtered, filtered_more = repository.list(
            verification_receipt_id=first_receipt.id,
            valid=True,
            limit=10,
        )
        assert filtered_more is False
        assert [item.id for item in filtered] == [first.id]

        with pytest.raises(
            IndependentM477VerificationReceiptM479PersistenceError,
            match="before_created_at and before_id",
        ):
            repository.list(before_id=uuid4(), limit=1)

        with pytest.raises(
            IndependentM477VerificationReceiptM479PersistenceError,
            match="timezone-aware",
        ):
            repository.list(before_created_at=datetime.now(), limit=1)
    finally:
        session.close()
        engine.dispose()


def test_m4_79_detects_tampered_persisted_receipt() -> None:
    engine, session = _session_m4_79()
    try:
        _, source_receipt, _, _ = _persist_m4_77_receipt(session)
        repository = IndependentM477VerificationReceiptM479Repository(session)
        record = repository.record(
            verification_receipt_id=source_receipt.id,
            recorded_by="ministry",
        )
        record.blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentM477VerificationReceiptM479PersistenceError,
            match="structurally invalid",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_79_detects_tampered_m4_77_source() -> None:
    engine, session = _session_m4_79()
    try:
        _, source_receipt, source_records, _ = _persist_m4_77_receipt(session)
        repository = IndependentM477VerificationReceiptM479Repository(session)
        record = repository.record(
            verification_receipt_id=source_receipt.id,
            recorded_by="ministry",
        )
        source_records[0].blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentM477VerificationReceiptM479PersistenceError,
            match="M4.78 independent reconstruction failed",
        ):
            repository.verify(record.id)
    finally:
        session.close()
        engine.dispose()


class _SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            self.session.rollback()
        return False


def _m4_79_path(suffix: str = "") -> str:
    return (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/m4-77-verification-receipts"
        + suffix
    )


def test_m4_79_post_persists_verification_receipt(monkeypatch) -> None:
    engine, session = _session_m4_79()
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.MINISTRY)
    try:
        _, source_receipt, _, _ = _persist_m4_77_receipt(session)
        monkeypatch.setattr(m4_79_api, "SessionLocal", lambda: _SessionContext(session))
        monkeypatch.setattr(m4_79_api, "append_audit_event", lambda **_: None)
        with TestClient(app) as client:
            response = client.post(
                _m4_79_path(f"/{source_receipt.id}/verification-receipts")
            )
        assert response.status_code == 200
        body = response.json()
        assert body["verification_receipt_id"] == str(source_receipt.id)
        assert body["recorded_by"] == "m4-79-test"
        assert body["verification"]["valid"] is True
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override
        session.close()
        engine.dispose()


def test_m4_79_post_requires_authentication(monkeypatch) -> None:
    previous_override = app.dependency_overrides.pop(get_current_principal, None)
    monkeypatch.setattr(database, "ENVIRONMENT", "test")
    monkeypatch.setattr(auth_module, "settings", Settings(environment="test"))
    try:
        with TestClient(app) as client:
            response = client.post(
                _m4_79_path(f"/{uuid4()}/verification-receipts")
            )
        assert response.status_code == 401
    finally:
        if previous_override is not None:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_79_post_requires_mfa(monkeypatch) -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="m4-79-no-mfa",
        role="admin",
        scope=Scope.MINISTRY,
        scope_id="ministry",
        mfa_verified=False,
    )
    try:
        response = TestClient(app).post(
            _m4_79_path(f"/{uuid4()}/verification-receipts")
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "MFA is required for privileged actions"
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_79_post_rejects_invalid_uuid() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.MINISTRY)
    try:
        response = TestClient(app).post(
            _m4_79_path("/not-a-uuid/verification-receipts")
        )
        assert response.status_code == 422
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_79_post_unknown_source_receipt_returns_404() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.MINISTRY)
    init_db()
    try:
        response = TestClient(app).post(
            _m4_79_path(f"/{uuid4()}/verification-receipts")
        )
        assert response.status_code == 404
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_79_openapi_routes_are_registered() -> None:
    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-77-verification-receipts"
    )
    paths = app.openapi()["paths"]
    assert (
        "post"
        in paths[prefix + "/{verification_receipt_id}/verification-receipts"]
    )
    assert "get" in paths[prefix + "/verification-history"]
    assert (
        "get"
        in paths[prefix + "/verification-receipts/{verification_id}/verify"]
    )


def test_m4_79_api_enforces_ministry_scope() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.SCHOOL)
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-77-verification-receipts/verification-history"
        )
        assert response.status_code == 403
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_79_unknown_verification_receipt_returns_404() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.MINISTRY)
    init_db()
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            f"m4-77-verification-receipts/verification-receipts/{uuid4()}/verify"
        )
        assert response.status_code == 404
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override
