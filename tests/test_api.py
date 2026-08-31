from fastapi.testclient import TestClient

from morva.api.app import app


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_payroll_calculation_route():
    response = client.post(
        "/api/v1/payroll/calculate",
        json={
            "employee_no": "E100",
            "period": "2026-09-01",
            "ruleset_version": "demo",
            "lines": [
                {
                    "code": "BASE",
                    "title": "Base",
                    "amount": "500000000",
                    "kind": "earning",
                    "taxable": True,
                    "pensionable": True,
                }
            ],
            "apply_demo_policy": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["employee_no"] == "E100"
    assert body["gross"] == "500000000"
    assert len(body["fingerprint"]) == 64


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
