from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from morva.api.app import app
from morva.persistence.core_hr_employment import EmploymentRecord
from morva.persistence.database import SessionLocal, init_db
from morva.persistence.models import EmployeeRecord, PersonnelOrderRecord
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope

app.dependency_overrides[get_current_principal] = lambda: Principal(
    user_id="order-admin",
    role="admin",
    scope=Scope.MINISTRY,
    scope_id="ministry",
    mfa_verified=True,
)
client = TestClient(app)


def _seed_employee() -> str:
    init_db()
    employee_no = "ORD-" + uuid4().hex[:10]
    with SessionLocal() as session:
        session.add(EmployeeRecord(employee_no=employee_no, source_employee_key="SRC-" + employee_no, national_id=str(uuid4().int)[-10:], first_name="Order", last_name="Employee", employment_type="permanent", status="active", organization_unit_id="ORG-TEST", position_id="POS-TEST", hire_date=date(2020, 1, 1)))
        session.add(EmploymentRecord(employee_no=employee_no, employment_type="permanent", organization_unit_id="ORG-TEST", position_id="POS-TEST", starts_on=date(2020, 1, 1), status="active"))
        session.commit()
    return employee_no


def test_personnel_order_registers_idempotently_and_filters_effective_date():
    employee_no = _seed_employee()
    payload = {
        "number": "ORD-1405-0001",
        "order_type": "promotion",
        "issue_date": "2026-01-10",
        "effective_from": "2026-02-01",
        "reference": "TODO: NEEDS-LEGAL-SOURCE",
        "lines": [{"code": "BASE", "amount": "125000000", "rule_code": "TODO: NEEDS-LEGAL-SOURCE"}],
    }
    first = client.post(f"/api/v1/hr/employees/{employee_no}/orders", json=payload)
    assert first.status_code == 201
    second = client.post(f"/api/v1/hr/employees/{employee_no}/orders", json=payload)
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    before = client.get(f"/api/v1/hr/employees/{employee_no}/orders", params={"effective_on": "2026-01-31"})
    after = client.get(f"/api/v1/hr/employees/{employee_no}/orders", params={"effective_on": "2026-02-01"})
    assert before.status_code == 200 and before.json()["items"] == []
    assert after.status_code == 200 and [item["order_no"] for item in after.json()["items"]] == ["ORD-1405-0001"]


def test_personnel_order_is_immutable_on_conflicting_content():
    employee_no = _seed_employee()
    base = {"number": "ORD-1405-0002", "order_type": "appointment", "issue_date": "2026-03-01", "effective_from": "2026-03-01", "lines": [{"code": "X", "amount": "10"}]}
    assert client.post(f"/api/v1/hr/employees/{employee_no}/orders", json=base).status_code == 201
    changed = {**base, "lines": [{"code": "X", "amount": "11"}]}
    response = client.post(f"/api/v1/hr/employees/{employee_no}/orders", json=changed)
    assert response.status_code == 409
    with SessionLocal() as session:
        record = session.query(PersonnelOrderRecord).filter(PersonnelOrderRecord.order_no == "ORD-1405-0002").one()
        assert Decimal(record.payload["lines"][0]["amount"]) == Decimal("10")
