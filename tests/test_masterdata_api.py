from uuid import uuid4

from fastapi.testclient import TestClient

from morva.api.app import app
from morva.persistence.database import init_db
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope

app.dependency_overrides[get_current_principal] = lambda: Principal(
    user_id="masterdata-admin",
    role="admin",
    scope=Scope.MINISTRY,
    scope_id="ministry",
    mfa_verified=True,
)
client = TestClient(app)


def test_position_master_data_create_and_effective_filter():
    init_db()
    code = "POS-" + uuid4().hex[:10]
    payload = {
        "code": code,
        "title": "Test Position",
        "occupational_group": "education",
        "grade": 5,
        "job_points": "125.5000",
        "full_time_educational": True,
        "effective_from": "2026-01-01",
        "effective_to": "2026-12-29",
        "active": True,
    }
    created = client.post("/api/v1/master-data/positions", json=payload)
    assert created.status_code == 201
    assert created.json()["code"] == code
    assert created.json()["job_points"] == "125.5000"

    active = client.get("/api/v1/master-data/positions", params={"effective_on": "2026-06-01"})
    assert active.status_code == 200
    assert any(item["code"] == code for item in active.json()["items"])

    inactive = client.get("/api/v1/master-data/positions", params={"effective_on": "2027-01-01"})
    assert inactive.status_code == 200
    assert all(item["code"] != code for item in inactive.json()["items"])


def test_position_master_data_rejects_invalid_effective_range():
    response = client.post(
        "/api/v1/master-data/positions",
        json={
            "code": "POS-" + uuid4().hex[:10],
            "title": "Invalid Position",
            "occupational_group": "education",
            "job_points": "0",
            "effective_from": "2026-12-31",
            "effective_to": "2026-01-01",
        },
    )
    assert response.status_code == 422


def test_organization_master_data_rejects_unknown_parent():
    response = client.post(
        "/api/v1/master-data/organizations",
        json={
            "code": "ORG-" + uuid4().hex[:10],
            "name": "Test Organization",
            "kind": "school",
            "parent_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert response.status_code == 422
