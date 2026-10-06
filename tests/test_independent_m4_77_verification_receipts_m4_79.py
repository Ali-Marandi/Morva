from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, inspect

import morva.persistence.database as database
from morva.api.app import app
from morva.persistence.database import init_db
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479PersistenceError,
    IndependentM477VerificationReceiptM479Record,
    IndependentM477VerificationReceiptM479Repository,
)
from morva.security.auth import get_current_principal
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
        _, second_receipt, _, _ = _persist_m4_77_receipt(session)
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
        in paths[prefix + "/{verification_receipt_id}/independent-verification-receipts"]
    )
    assert "get" in paths[prefix + "/independent-verification-history"]
    assert (
        "get"
        in paths[prefix + "/independent-verification-receipts/{verification_id}/verify"]
    )


def test_m4_79_api_enforces_ministry_scope() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.SCHOOL)
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-77-verification-receipts/independent-verification-history"
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
            f"m4-77-verification-receipts/independent-verification-receipts/{uuid4()}/verify"
        )
        assert response.status_code == 404
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override
