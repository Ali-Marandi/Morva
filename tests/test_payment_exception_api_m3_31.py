from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from morva.api.app import app
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope

app.dependency_overrides[get_current_principal] = lambda: Principal(
    user_id="m3-31-admin",
    role="admin",
    scope=Scope.MINISTRY,
    scope_id="ministry",
    mfa_verified=True,
)
@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def _new_exception() -> tuple[str, str]:
    return f"EX-{uuid4().hex}", f"ITEM-{uuid4().hex}"


def test_payment_exception_workflow_is_provider_neutral_and_idempotent(client):
    exception_id, payment_item_id = _new_exception()
    create = client.post(
        "/api/v1/payment-exceptions",
        json={
            "exception_id": exception_id,
            "payment_item_id": payment_item_id,
            "exception_type": "unresolved_mismatch",
            "reason": "Settlement amount differs from the authoritative payment item.",
        },
    )
    assert create.status_code == 201
    assert create.json()["status"] == "open"

    listed = client.get(f"/api/v1/payment-exceptions?payment_item_id={payment_item_id}")
    assert listed.status_code == 200
    assert [item["exception_id"] for item in listed.json()] == [exception_id]

    key = f"resolve-{uuid4().hex}"
    resolve_payload = {
        "reason": "Reviewed against approved reconciliation evidence.",
        "evidence_ref": "recon://case/M3-31/001",
    }
    resolved = client.post(
        f"/api/v1/payment-exceptions/{exception_id}/resolve",
        headers={"Idempotency-Key": key},
        json=resolve_payload,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    replayed = client.post(
        f"/api/v1/payment-exceptions/{exception_id}/resolve",
        headers={"Idempotency-Key": key},
        json=resolve_payload,
    )
    assert replayed.status_code == 200
    assert replayed.json()["fingerprint"] == resolved.json()["fingerprint"]

    open_only = client.get(f"/api/v1/payment-exceptions?payment_item_id={payment_item_id}")
    assert open_only.status_code == 200
    assert open_only.json() == []

    all_records = client.get(
        f"/api/v1/payment-exceptions?payment_item_id={payment_item_id}&include_resolved=true"
    )
    assert all_records.status_code == 200
    assert all_records.json()[0]["status"] == "resolved"

    events = client.get(f"/api/v1/payment-exceptions/{exception_id}/events")
    assert events.status_code == 200
    assert len(events.json()) == 1
    assert events.json()[0]["idempotency_key"] == key


def test_payment_exception_resolution_rejects_second_non_idempotent_resolution(client):
    exception_id, _ = _new_exception()
    create = client.post(
        "/api/v1/payment-exceptions",
        json={
            "exception_id": exception_id,
            "payment_item_id": "ITEM-SECOND-RESOLUTION",
            "exception_type": "return",
            "reason": "Returned payment item requires review.",
        },
    )
    assert create.status_code == 201

    first = client.post(
        f"/api/v1/payment-exceptions/{exception_id}/resolve",
        headers={"Idempotency-Key": "resolution-first-123"},
        json={"reason": "Evidence reviewed.", "evidence_ref": "recon://case/002"},
    )
    assert first.status_code == 200

    second = client.post(
        f"/api/v1/payment-exceptions/{exception_id}/resolve",
        headers={"Idempotency-Key": "resolution-second-456"},
        json={"reason": "Different attempted resolution.", "evidence_ref": "recon://case/003"},
    )
    assert second.status_code == 409
