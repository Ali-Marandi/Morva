from __future__ import annotations

from hashlib import sha256
import json
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from morva.api.app import app
import morva.security.auth as auth_module
from morva.persistence.historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    HistoricalM474VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
)
from morva.persistence.database import init_db
from morva.runtime.config import Settings
from morva.runtime.independent_historical_m4_74_verification_receipt_history_integrity_m4_76 import (
    IndependentHistoricalM474VerificationReceiptHistoryIntegrityError,
    independently_verify_historical_m4_74_verification_receipt_history_integrity,
)
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope
from tests.test_historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    _persist_m4_74_receipt,
    _session_m4_75,
)


def _source_records(session):
    statement = select(
        IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord
    ).order_by(
        IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.created_at.asc(),
        IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord.id.asc(),
    )
    return list(session.scalars(statement).all())


def test_m4_76_independently_verifies_m4_75_snapshot() -> None:
    engine, session = _session_m4_75()
    try:
        _persist_m4_74_receipt(session)
        snapshot = HistoricalM474VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        result = independently_verify_historical_m4_74_verification_receipt_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is True
        assert result.blockers == ()
        assert result.persisted_fingerprint == result.reconstructed_fingerprint
        assert (
            result.persisted_history_fingerprint
            == result.reconstructed_history_fingerprint
        )
    finally:
        session.close()
        engine.dispose()


def test_m4_76_respects_snapshot_point_in_time_boundary() -> None:
    engine, session = _session_m4_75()
    try:
        _persist_m4_74_receipt(session, "a" * 64)
        snapshot = HistoricalM474VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        _persist_m4_74_receipt(session, "b" * 64)
        result = independently_verify_historical_m4_74_verification_receipt_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is True
        assert result.reconstructed_record_count == 1
    finally:
        session.close()
        engine.dispose()


def test_m4_76_detects_tampered_snapshot() -> None:
    engine, session = _session_m4_75()
    try:
        _persist_m4_74_receipt(session)
        snapshot = HistoricalM474VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        snapshot.record_count = 2
        snapshot.fingerprint = sha256(
            json.dumps(
                {
                    "integrity_version": snapshot.integrity_version,
                    "record_count": snapshot.record_count,
                    "valid_count": snapshot.valid_count,
                    "history_fingerprint": snapshot.history_fingerprint,
                },
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        session.flush()
        result = independently_verify_historical_m4_74_verification_receipt_history_integrity(
            snapshot=snapshot,
            source_records=_source_records(session),
        )
        assert result.valid is False
        assert "M475_RECORD_COUNT_MISMATCH" in result.blockers
        assert "M475_INTEGRITY_FINGERPRINT_MISMATCH" in result.blockers
    finally:
        session.close()
        engine.dispose()


def test_m4_76_fails_closed_on_invalid_source_record() -> None:
    engine, session = _session_m4_75()
    try:
        _persist_m4_74_receipt(session)
        snapshot = HistoricalM474VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        source = _source_records(session)[0]
        source.verification_fingerprint = "f" * 64
        session.flush()
        with pytest.raises(
            IndependentHistoricalM474VerificationReceiptHistoryIntegrityError,
            match="M4.74 source verification record is structurally invalid",
        ):
            independently_verify_historical_m4_74_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


def test_m4_76_rejects_invalid_persisted_snapshot_structure() -> None:
    engine, session = _session_m4_75()
    try:
        _persist_m4_74_receipt(session)
        snapshot = HistoricalM474VerificationReceiptHistoryIntegrityRepository(
            session
        ).capture(captured_by="ministry")
        snapshot.fingerprint = "not-a-sha"
        session.flush()
        with pytest.raises(
            IndependentHistoricalM474VerificationReceiptHistoryIntegrityError,
            match=(
                "persisted M4.75 verification-receipt history integrity "
                "snapshot is structurally invalid"
            ),
        ):
            independently_verify_historical_m4_74_verification_receipt_history_integrity(
                snapshot=snapshot,
                source_records=_source_records(session),
            )
    finally:
        session.close()
        engine.dispose()


_M4_76_VERIFY_PATH = (
    "/api/v1/integration-execution/readiness/convergence/freshness/"
    "policy-registry-snapshot-bound/receipt-lineage/"
    "independent-verification-history-integrity/"
    "m4-74-verification-receipt-history-integrity-snapshots/"
    "{snapshot_id}/verify-independent"
)


def test_m4_76_openapi_route_is_registered() -> None:
    assert "get" in app.openapi()["paths"][
        _M4_76_VERIFY_PATH.replace("{snapshot_id}", "{snapshot_id}")
    ]


def test_m4_76_verification_endpoint_requires_authentication(monkeypatch) -> None:
    previous = app.dependency_overrides.pop(get_current_principal, None)
    monkeypatch.setattr(auth_module, "settings", Settings(environment="test"))
    try:
        response = TestClient(app).get(
            _M4_76_VERIFY_PATH.format(snapshot_id=uuid4()),
        )
        assert response.status_code == 401
    finally:
        if previous is not None:
            app.dependency_overrides[get_current_principal] = previous


def test_m4_76_verification_endpoint_returns_404_for_unknown_snapshot() -> None:
    previous = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="m4-76-test",
        role="admin",
        scope=Scope.MINISTRY,
        scope_id="test",
        mfa_verified=True,
    )
    init_db()
    try:
        response = TestClient(app).get(
            _M4_76_VERIFY_PATH.format(snapshot_id=uuid4()),
        )
        assert response.status_code == 404
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous
