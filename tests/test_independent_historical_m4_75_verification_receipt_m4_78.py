from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from morva.api.app import app
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
)
from morva.persistence.independent_historical_m4_75_verification_receipts_m4_77 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository,
)
from morva.runtime.independent_historical_m4_75_verification_receipt_m4_78 import (
    IndependentHistoricalM475VerificationReceiptM478Error,
    independently_verify_historical_m4_75_verification_receipt_m4_77,
)
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope
from tests.test_independent_historical_m4_75_verification_receipts_m4_77 import (
    _persist_m4_75_snapshot,
    _session_m4_77,
)


def _persist_m4_77_receipt(session):
    snapshot = _persist_m4_75_snapshot(session)
    repository = IndependentHistoricalM475VerificationReceiptHistoryIntegrityRepository(
        session
    )
    receipt = repository.record(snapshot_id=snapshot.id, recorded_by="ministry")
    source_repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
        session
    )
    source_query = (
        select(IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord)
        .where(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.created_at
            < snapshot.created_at
        )
        .order_by(
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.created_at.asc(),
            IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.id.asc(),
        )
    )
    return (
        snapshot,
        receipt,
        list(session.scalars(source_query).all()),
        source_repository,
    )


def test_m4_78_verifies_persisted_m4_77_receipt() -> None:
    engine, session = _session_m4_77()
    try:
        snapshot, receipt, source_records, source_repository = _persist_m4_77_receipt(
            session
        )
        result = independently_verify_historical_m4_75_verification_receipt_m4_77(
            receipt=receipt,
            snapshot=snapshot,
            source_records=source_records,
            source_repository=source_repository,
        )
        assert result.valid is True
        assert result.blockers == ()
        assert (
            result.persisted_verification_fingerprint
            == result.reconstructed_verification_fingerprint
        )
        assert result.persisted_snapshot_id == result.reconstructed_snapshot_id
    finally:
        session.close()
        engine.dispose()


def test_m4_78_detects_tampered_persisted_receipt() -> None:
    engine, session = _session_m4_77()
    try:
        snapshot, receipt, source_records, source_repository = _persist_m4_77_receipt(
            session
        )
        receipt.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentHistoricalM475VerificationReceiptM478Error,
            match="persisted M4.77 verification receipt is structurally invalid",
        ):
            independently_verify_historical_m4_75_verification_receipt_m4_77(
                receipt=receipt,
                snapshot=snapshot,
                source_records=source_records,
                source_repository=source_repository,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_78_detects_tampered_source_receipt() -> None:
    engine, session = _session_m4_77()
    try:
        snapshot, receipt, source_records, source_repository = _persist_m4_77_receipt(
            session
        )
        source_records[0].blockers_json = '["TAMPERED"]'
        session.flush()
        with pytest.raises(
            IndependentHistoricalM475VerificationReceiptM478Error,
            match="M4.78 independent source reconstruction failed",
        ):
            independently_verify_historical_m4_75_verification_receipt_m4_77(
                receipt=receipt,
                snapshot=snapshot,
                source_records=source_records,
                source_repository=source_repository,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_78_detects_wrong_snapshot_binding() -> None:
    engine, session = _session_m4_77()
    try:
        snapshot, receipt, source_records, source_repository = _persist_m4_77_receipt(
            session
        )
        other_snapshot = _persist_m4_75_snapshot(session, "b" * 64)
        result = independently_verify_historical_m4_75_verification_receipt_m4_77(
            receipt=receipt,
            snapshot=other_snapshot,
            source_records=source_records,
            source_repository=source_repository,
        )
        assert result.valid is False
        assert "M478_SNAPSHOT_BINDING_MISMATCH" in result.blockers
    finally:
        session.close()
        engine.dispose()


def test_m4_78_openapi_route_is_registered() -> None:
    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/"
        "independent-verification-history-integrity/"
        "m4-77-verification-receipts/{verification_id}/verify-independent"
    )
    assert "get" in app.openapi()["paths"][path]


def test_m4_78_api_rejects_non_ministry_scope() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="m4-78-test",
        role="admin",
        scope=Scope.SCHOOL,
        scope_id="school-1",
        mfa_verified=True,
    )
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            f"m4-77-verification-receipts/{uuid4()}/verify-independent"
        )
        assert response.status_code == 403
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override


def test_m4_78_api_returns_404_for_unknown_receipt() -> None:
    previous_override = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="m4-78-test",
        role="admin",
        scope=Scope.MINISTRY,
        scope_id="ministry-1",
        mfa_verified=True,
    )
    try:
        response = TestClient(app).get(
            "/api/v1/integration-execution/readiness/convergence/freshness/"
            "policy-registry-snapshot-bound/receipt-lineage/"
            "independent-verification-history-integrity/"
            f"m4-77-verification-receipts/{uuid4()}/verify-independent"
        )
        assert response.status_code == 404
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_override
