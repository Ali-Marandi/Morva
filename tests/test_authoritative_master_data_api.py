from fastapi.testclient import TestClient

from morva.api.app import app
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope


app.dependency_overrides[get_current_principal] = lambda: Principal(
    user_id="authoritative-masterdata-validator",
    role="admin",
    scope=Scope.MINISTRY,
    scope_id="ministry",
    mfa_verified=True,
)

client = TestClient(app)


def test_authoritative_master_data_integrity_endpoint_is_authenticated_and_structured():
    response = client.get("/api/v1/master-data/authoritative-integrity")

    assert response.status_code == 200
    payload = response.json()
    assert {"blocking", "findings"}.issubset(payload)
    assert isinstance(payload["blocking"], bool)
    assert isinstance(payload["findings"], list)


def test_authoritative_master_data_integrity_endpoint_requires_personnel_read_permission():
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="read-only-validator",
        role="employee",
        scope=Scope.MINISTRY,
        scope_id="ministry",
        mfa_verified=True,
    )
    try:
        response = client.get("/api/v1/master-data/authoritative-integrity")
        assert response.status_code == 403
    finally:
        app.dependency_overrides[get_current_principal] = lambda: Principal(
            user_id="authoritative-masterdata-validator",
            role="admin",
            scope=Scope.MINISTRY,
            scope_id="ministry",
            mfa_verified=True,
        )
