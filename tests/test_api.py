from uuid import uuid4

from fastapi.testclient import TestClient

from morva.api.app import app
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope


app.dependency_overrides[get_current_principal] = lambda: Principal(
    user_id="test-user",
    role="admin",
    scope=Scope.MINISTRY,
    scope_id="test",
    mfa_verified=True,
)
client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_legacy_payroll_calculation_route_is_blocked():
    response = client.post(
        "/api/v1/payroll/calculate",
        json={
            "employee_no": "E100",
            "period": "2026-09-01",
            "ruleset_version": "demo",
            "lines": [{"code": "BASE", "title": "Base", "amount": "500000000", "kind": "earning"}],
        },
    )
    assert response.status_code == 410


def test_payroll_run_is_persisted_before_calculation():
    org = "TEST-" + uuid4().hex[:8]
    response = client.post(
        "/api/v1/payroll/runs",
        json={
            "period": "2099-12",
            "ruleset_version": "review_required",
            "organization_unit_id": org,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"

    calc = client.post(f"/api/v1/payroll/runs/{body['id']}/calculate")
    assert calc.status_code == 409
    assert "data_received state" in calc.json()["detail"]


def test_rule_evaluation_route():
    response = client.post(
        "/api/v1/rules/evaluate",
        json={
            "rule": {
                "code": "PERCENT",
                "title": "Percentage",
                "effective_from": "2026-01-01",
                "expression": {
                    "op": "mul",
                    "args": [
                        {"op": "value", "name": "base"},
                        {"op": "value", "name": "rate"},
                    ],
                },
                "legal_reference": "TEST-ONLY",
            },
            "effective_date": "2026-09-01",
            "values": {"base": "100", "rate": "0.15"},
        },
    )
    assert response.status_code == 200
    assert response.json()["amount"] == "15.00"
