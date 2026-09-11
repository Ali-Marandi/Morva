from datetime import date, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from morva.api.app import app
from morva.persistence.core_hr_employment import EmploymentRecord
from morva.persistence.database import SessionLocal, init_db
from morva.persistence.models import EmployeeRecord
from morva.personnel.order_approval_policy import register_approval_policy
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope


POLICY_CODE = "TEST-PERSONNEL-ORDER-APPROVAL"


def _principal(user_id: str, role: str = "admin", mfa_verified: bool = True) -> Principal:
    return Principal(user_id=user_id, role=role, scope=Scope.MINISTRY, scope_id="ministry", mfa_verified=mfa_verified)


@pytest.fixture(autouse=True)
def _principal_override() -> None:
    app.dependency_overrides[get_current_principal] = lambda: _principal("order-admin")
    yield
    app.dependency_overrides.pop(get_current_principal, None)


client = TestClient(app)


def _seed_policy() -> None:
    init_db()
    with SessionLocal() as session:
        register_approval_policy(
            session,
            policy_code=POLICY_CODE,
            version="1",
            order_types=["promotion", "appointment"],
            required_submission_role="admin",
            required_decision_role="personnel_approver",
            source_reference="fixture://personnel-order-policy",
            source_hash="a" * 64,
            approved_by="fixture-policy-authority",
            approved_at=datetime(2026, 1, 1),
        )
        session.commit()


def _seed_employee() -> str:
    init_db()
    _seed_policy()
    employee_no = "ORD-" + uuid4().hex[:10]
    with SessionLocal() as session:
        session.add(EmployeeRecord(employee_no=employee_no, source_employee_key="SRC-" + employee_no, national_id=str(uuid4().int)[-10:], first_name="Order", last_name="Employee", employment_type="permanent", status="active", organization_unit_id="ORG-TEST", position_id="POS-TEST", hire_date=date(2020, 1, 1)))
        session.add(EmploymentRecord(employee_no=employee_no, employment_type="permanent", organization_unit_id="ORG-TEST", position_id="POS-TEST", starts_on=date(2020, 1, 1), status="active"))
        session.commit()
    return employee_no


def _create_order(employee_no: str, number: str) -> None:
    payload = {"number": number, "order_type": "promotion", "issue_date": "2026-01-10", "effective_from": "2026-02-01", "reference": "TODO: NEEDS-LEGAL-SOURCE", "lines": [{"code": "BASE", "amount": "125000000", "rule_code": "TODO: NEEDS-LEGAL-SOURCE"}]}
    response = client.post(f"/api/v1/hr/employees/{employee_no}/orders", json=payload)
    assert response.status_code == 201


def test_personnel_order_is_pending_until_distinct_approved():
    employee_no = _seed_employee()
    _create_order(employee_no, "ORD-1405-1001")
    pending = client.get(f"/api/v1/hr/employees/{employee_no}/orders/ORD-1405-1001/approval")
    assert pending.status_code == 200
    assert pending.json()["status"] == "pending"
    assert pending.json()["submitted_by"] == "order-admin"
    effective_before = client.get(f"/api/v1/hr/employees/{employee_no}/orders", params={"effective_on": "2026-02-01"})
    assert effective_before.status_code == 200 and effective_before.json()["items"] == []
    same_actor = client.post(f"/api/v1/hr/employees/{employee_no}/orders/ORD-1405-1001/approval", json={"decision": "approved", "policy_code": POLICY_CODE})
    assert same_actor.status_code == 409
    app.dependency_overrides[get_current_principal] = lambda: _principal("order-approver", role="personnel_approver")
    approved = client.post(f"/api/v1/hr/employees/{employee_no}/orders/ORD-1405-1001/approval", json={"decision": "approved", "reason": "reviewed", "policy_code": POLICY_CODE})
    assert approved.status_code == 200
    effective_after = client.get(f"/api/v1/hr/employees/{employee_no}/orders", params={"effective_on": "2026-02-01"})
    assert [item["order_no"] for item in effective_after.json()["items"]] == ["ORD-1405-1001"]
    duplicate = client.post(f"/api/v1/hr/employees/{employee_no}/orders/ORD-1405-1001/approval", json={"decision": "rejected", "policy_code": POLICY_CODE})
    assert duplicate.status_code == 409


def test_personnel_order_approval_requires_mfa():
    employee_no = _seed_employee()
    _create_order(employee_no, "ORD-1405-1002")
    app.dependency_overrides[get_current_principal] = lambda: _principal("order-approver-no-mfa", role="personnel_approver", mfa_verified=False)
    response = client.post(f"/api/v1/hr/employees/{employee_no}/orders/ORD-1405-1002/approval", json={"decision": "approved", "policy_code": POLICY_CODE})
    assert response.status_code == 403


def test_rejected_personnel_order_never_becomes_effective():
    employee_no = _seed_employee()
    _create_order(employee_no, "ORD-1405-1003")
    app.dependency_overrides[get_current_principal] = lambda: _principal("order-approver", role="personnel_approver")
    response = client.post(f"/api/v1/hr/employees/{employee_no}/orders/ORD-1405-1003/approval", json={"decision": "rejected", "reason": "insufficient evidence", "policy_code": POLICY_CODE})
    assert response.status_code == 200
    effective = client.get(f"/api/v1/hr/employees/{employee_no}/orders", params={"effective_on": "2026-02-01"})
    assert effective.status_code == 200
    assert all(item["order_no"] != "ORD-1405-1003" for item in effective.json()["items"])
