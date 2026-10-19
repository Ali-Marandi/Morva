from __future__ import annotations

import json
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

import morva.api.v1.m4_80_independent_verification as m4_80_api
from morva.api.app import app
from morva.persistence.historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    HistoricalM474VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479Repository,
)
from morva.runtime.config import Settings
from morva.runtime.independent_m4_77_verification_receipt_m4_80 import (
    IndependentM477VerificationReceiptM480Error,
    independently_verify_m4_79_verification_receipt,
)
import morva.security.auth as auth_module
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope
from tests.test_independent_historical_m4_75_verification_receipt_m4_78 import (
    _persist_m4_77_receipt,
)
from tests.test_independent_m4_77_verification_receipts_m4_79 import _session_m4_79


def _principal(scope: Scope) -> Principal:
    return Principal(
        user_id="m4-80-test",
        role="admin",
        scope=scope,
        scope_id="test",
        mfa_verified=True,
    )


def _seed_m4_79_receipt(session):
    _, source_receipt, _, _ = _persist_m4_77_receipt(session)
    receipt = IndependentM477VerificationReceiptM479Repository(session).record(
        verification_receipt_id=source_receipt.id,
        recorded_by="ministry",
    )
    snapshot = session.get(
        HistoricalM474VerificationReceiptHistoryIntegrityRecord,
        source_receipt.snapshot_id,
    )
    assert snapshot is not None
    source_records = list(
        session.scalars(
            select(IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord)
            .where(
                IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.created_at
                < snapshot.created_at
            )
            .order_by(
                IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.created_at.asc(),
                IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.id.asc(),
            )
        ).all()
    )
    source_repository = IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository(
        session
    )
    return source_receipt, receipt, snapshot, source_records, source_repository


def _verify(source_receipt, receipt, snapshot, source_records, source_repository):
    return independently_verify_m4_79_verification_receipt(
        receipt=receipt,
        source_receipt=source_receipt,
        snapshot=snapshot,
        source_records=source_records,
        source_repository=source_repository,
    )


def test_m4_80_independently_reconstructs_persisted_m4_79_receipt() -> None:
    engine, session = _session_m4_79()
    try:
        source_receipt, receipt, snapshot, source_records, source_repository = (
            _seed_m4_79_receipt(session)
        )
        verification = _verify(
            source_receipt,
            receipt,
            snapshot,
            source_records,
            source_repository,
        )
        repeated = _verify(
            source_receipt,
            receipt,
            snapshot,
            source_records,
            source_repository,
        )
        assert verification.valid is True
        assert verification.blockers == ()
        assert verification.persisted_fingerprint == verification.reconstructed_fingerprint
        assert verification.verification_fingerprint == repeated.verification_fingerprint
    finally:
        session.close()
        engine.dispose()


def test_m4_80_fails_closed_on_tampered_m4_79_receipt() -> None:
    engine, session = _session_m4_79()
    try:
        source_receipt, receipt, snapshot, source_records, source_repository = (
            _seed_m4_79_receipt(session)
        )
        receipt.blockers_json = json.dumps(["TAMPERED"], separators=(",", ":"))
        session.flush()
        with pytest.raises(
            IndependentM477VerificationReceiptM480Error,
            match="structurally invalid",
        ):
            _verify(
                source_receipt,
                receipt,
                snapshot,
                source_records,
                source_repository,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_80_rejects_wrong_source_snapshot_binding() -> None:
    engine, session = _session_m4_79()
    try:
        source_receipt, receipt, snapshot, source_records, source_repository = (
            _seed_m4_79_receipt(session)
        )
        wrong_snapshot = HistoricalM474VerificationReceiptHistoryIntegrityRecord(
            id=uuid4(),
            integrity_version=snapshot.integrity_version,
            record_count=snapshot.record_count,
            valid_count=snapshot.valid_count,
            history_fingerprint=snapshot.history_fingerprint,
            fingerprint=snapshot.fingerprint,
            captured_by=snapshot.captured_by,
            created_at=snapshot.created_at,
        )
        with pytest.raises(
            IndependentM477VerificationReceiptM480Error,
            match="different M4.75 snapshot",
        ):
            _verify(
                source_receipt,
                receipt,
                wrong_snapshot,
                source_records,
                source_repository,
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_80_openapi_route_is_registered() -> None:
    path = (
        "/api/v1"
        + m4_80_api._BASE_PATH
        + "/{verification_id}/verify-independent"
    )
    assert "get" in app.openapi()["paths"][path]


def test_m4_80_verification_requires_authentication_and_ministry_scope(
    monkeypatch,
) -> None:
    previous = app.dependency_overrides.pop(get_current_principal, None)
    monkeypatch.setattr(auth_module, "settings", Settings(environment="test"))
    path = "/api/v1" + m4_80_api._BASE_PATH + f"/{uuid4()}/verify-independent"
    try:
        with TestClient(app) as client:
            unauthenticated = client.get(path)
        assert unauthenticated.status_code == 401

        app.dependency_overrides[get_current_principal] = (
            lambda: _principal(next(scope for scope in Scope if scope is not Scope.MINISTRY))
        )
        with TestClient(app) as client:
            out_of_scope = client.get(path)
        assert out_of_scope.status_code == 403
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous


def test_m4_80_api_returns_fresh_verification(monkeypatch) -> None:
    engine, session = _session_m4_79()
    previous = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = (
        lambda: _principal(Scope.MINISTRY)
    )
    try:
        _, receipt, _, _, _ = _seed_m4_79_receipt(session)
        receipt_id = receipt.id
        session.commit()
        session.close()

        request_sessions = sessionmaker(
            bind=engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )
        monkeypatch.setattr(m4_80_api, "SessionLocal", request_sessions)
        with TestClient(app) as client:
            response = client.get(
                "/api/v1"
                + m4_80_api._BASE_PATH
                + f"/{receipt_id}/verify-independent"
            )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["id"] == str(receipt_id)
        assert payload["verification"]["valid"] is True
        assert payload["verification"]["blockers"] == []
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous
        session.close()
        engine.dispose()
