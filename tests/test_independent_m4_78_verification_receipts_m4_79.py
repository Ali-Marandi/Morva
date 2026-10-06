from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from morva.api.app import app
from morva.persistence.independent_historical_m4_75_verification_receipts_m4_77 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_m4_78_verification_receipts_m4_79 import (
    IndependentM478VerificationReceiptM479PersistenceError,
    IndependentM478VerificationReceiptM479Record,
    IndependentM478VerificationReceiptM479Repository,
)
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope
from tests.test_independent_historical_m4_75_verification_receipts_m4_77 import (
    _persist_m4_75_snapshot,
    _session_m4_77,
)


def _session_m4_79():
    engine, session = _session_m4_77()
    IndependentM478VerificationReceiptM479Record.__table__.create(bind=engine, checkfirst=True)
    return engine, session


def _persist_m4_78_receipt(session):
    snapshot = _persist_m4_75_snapshot(session)
    return IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(session).record(
        snapshot_id=snapshot.id,
        recorded_by="ministry",
    )


def _principal(scope: Scope) -> Principal:
    return Principal(
        user_id="m4-79-test",
        role="admin",
        scope=scope,
        scope_id="test",
        mfa_verified=True,
    )


def test_m4_79_records_and_reverifies_m4_78_result() -> None:
    engine, session = _session_m4_79()
    try:
        source = _persist_m4_78_receipt(session)
        repository = IndependentM478VerificationReceiptM479Repository(session)
        record = repository.record(verification_receipt_id=source.id, recorded_by="ministry")
        assert record.to_verification().valid is True
        assert record.to_verification().verification_receipt_id == source.id
        assert repository.verify(record.id).id == record.id
        assert repository.record(verification_receipt_id=source.id, recorded_by="ministry").id == record.id
    finally:
        session.close()
        engine.dispose()


def test_m4_79_rejects_second_actor_for_same_fingerprint() -> None:
    engine, session = _session_m4_79()
    try:
        source = _persist_m4_78_receipt(session)
        repository = IndependentM478VerificationReceiptM479Repository(session)
        repository.record(verification_receipt_id=source.id, recorded_by="ministry")
        with pytest.raises(IndependentM478VerificationReceiptM479PersistenceError, match="different actor"):
            repository.record(verification_receipt_id=source.id, recorded_by="auditor")
    finally:
        session.close()
        engine.dispose()


def test_m4_79_cursor_history_and_filters() -> None:
    engine, session = _session_m4_79()
    try:
        first_source = _persist_m4_78_receipt(session)
        first_record = IndependentM478VerificationReceiptM479Repository(session).record(
            verification_receipt_id=first_source.id, recorded_by="ministry"
        )
        second_source = _persist_m4_78_receipt(session)
        repository = IndependentM478VerificationReceiptM479Repository(session)
        second_record = repository.record(
            verification_receipt_id=second_source.id, recorded_by="ministry"
        )
        page, has_more = repository.list(limit=1)
        assert has_more is True
        assert page[0].id == second_record.id
        next_page, next_has_more = repository.list(
            before_created_at=page[0].created_at, before_id=page[0].id, limit=1
        )
        assert next_has_more is False
        assert next_page[0].id == first_record.id
        filtered, more = repository.list(verification_receipt_id=first_source.id, valid=True)
        assert more is False
        assert [item.id for item in filtered] == [first_record.id]
    finally:
        session.close()
        engine.dispose()


def test_m4_79_detects_tampered_persisted_receipt() -> None:
    engine, session = _session_m4_79()
    try:
        source = _persist_m4_78_receipt(session)
        record = IndependentM478VerificationReceiptM479Repository(session).record(
            verification_receipt_id=source.id, recorded_by="ministry"
        )
        record.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(IndependentM478VerificationReceiptM479PersistenceError, match="structurally invalid"):
            IndependentM478VerificationReceiptM479Repository(session).verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_79_detects_tampered_m4_77_source() -> None:
    engine, session = _session_m4_79()
    try:
        source = _persist_m4_78_receipt(session)
        record = IndependentM478VerificationReceiptM479Repository(session).record(
            verification_receipt_id=source.id, recorded_by="ministry"
        )
        source.persisted_fingerprint = "0" * 64
        session.flush()
        with pytest.raises(IndependentM478VerificationReceiptM479PersistenceError, match="M4.78 independent reconstruction failed"):
            IndependentM478VerificationReceiptM479Repository(session).verify(record.id)
    finally:
        session.close()
        engine.dispose()


def test_m4_79_unknown_source_returns_not_found() -> None:
    engine, session = _session_m4_79()
    try:
        with pytest.raises(IndependentM478VerificationReceiptM479PersistenceError, match="M4.77 independent verification receipt not found"):
            IndependentM478VerificationReceiptM479Repository(session).record(
                verification_receipt_id=uuid4(), recorded_by="ministry"
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_79_openapi_routes_are_registered() -> None:
    prefix = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/m4-78-verification-receipts"
    )
    paths = app.openapi()["paths"]
    assert "post" in paths[prefix + "/{verification_receipt_id}/verification-receipts"]
    assert "get" in paths[prefix + "/verification-history"]
    assert "get" in paths[prefix + "/verification-receipts/{verification_id}/verify"]


def test_m4_79_api_rejects_non_ministry_scope() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.SCHOOL)
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            "m4-78-verification-receipts/verification-history"
        )
        assert response.status_code == 403
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_79_unknown_receipt_api_returns_404() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: _principal(Scope.MINISTRY)
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            f"independent-verification-history-integrity/m4-78-verification-receipts/verification-receipts/{uuid4()}/verify"
        )
        assert response.status_code == 404
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override
