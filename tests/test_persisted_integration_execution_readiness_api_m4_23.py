from __future__ import annotations

from fastapi.testclient import TestClient

from morva.api.app import app
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope


app.dependency_overrides[get_current_principal] = lambda: Principal(
    user_id="m4-23-api-test",
    role="admin",
    scope=Scope.MINISTRY,
    scope_id="ministry",
    mfa_verified=True,
)


def test_m4_23_verify_route_is_registered():
    path = "/api/v1/integration-execution/readiness/verify"
    operation = app.openapi()["paths"][path]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert operation["responses"]["404"]["description"]
    assert operation["responses"]["409"]["description"]


def test_m4_23_verify_route_does_not_expose_write_methods():
    path = "/api/v1/integration-execution/readiness/verify"
    methods = set(app.openapi()["paths"][path])
    assert methods == {"get"}


def test_m4_23_verify_route_rejects_invalid_candidate_sha():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/integration-execution/readiness/verify",
            params={"candidate_sha": "x" * 40},
        )

    assert response.status_code == 422
    assert "candidate_sha" in response.json()["detail"]


def test_m4_23_verify_route_rejects_invalid_environment():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/integration-execution/readiness/verify",
            params={
                "candidate_sha": "b" * 40,
                "target_environment": "production",
            },
        )

    assert response.status_code == 422
