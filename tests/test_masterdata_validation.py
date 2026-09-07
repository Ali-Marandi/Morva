from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient

from morva.api.app import app
from morva.persistence.database import SessionLocal, init_db
from morva.persistence.domain_extensions import AssignmentRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import EmployeeRecord, PersonnelSnapshotRecord
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope


app.dependency_overrides[get_current_principal] = lambda: Principal(
    user_id="masterdata-validator",
    role="admin",
    scope=Scope.MINISTRY,
    scope_id="ministry",
    mfa_verified=True,
)
client = TestClient(app)


def test_masterdata_integrity_accepts_resolvable_references():
    init_db()
    org = OrganizationUnitRecord(code="ORG-" + uuid4().hex[:8], name="Test Org", kind="district")
    position = PositionRecord(code="POS-" + uuid4().hex[:8], title="Test Position", occupational_group="education")
    with SessionLocal() as session:
        session.add_all([org, position])
        session.flush()
        employee_no = "MD-" + uuid4().hex[:8]
        session.add(
            EmployeeRecord(
                employee_no=employee_no,
                source_employee_key="SRC-" + employee_no,
                national_id=str(uuid4().int)[-10:],
                first_name="Master",
                last_name="Data",
                employment_type="permanent",
                status="active",
                organization_unit_id=str(org.id),
                position_id=position.code,
                hire_date=date(2020, 1, 1),
            )
        )
        session.add(
            AssignmentRecord(
                employee_no=employee_no,
                organization_code=org.code,
                position_code=position.code,
                starts_on=date(2026, 1, 1),
            )
        )
        session.add(
            PersonnelSnapshotRecord(
                employee_no=employee_no,
                effective_period="2026-01",
                effective_date=date(2026, 1, 1),
                organization_unit_id=str(org.id),
                position_id=position.code,
                employment_type="permanent",
                employment_status="active",
                source_hash="a" * 64,
                snapshot_hash="b" * 64,
                order_numbers=[],
                components={},
            )
        )
        session.commit()

    response = client.get("/api/v1/master-data/integrity")
    assert response.status_code == 200
    body = response.json()
    assert body["blocking"] is False
    assert body["findings"] == []


def test_masterdata_integrity_blocks_unresolved_employee_references():
    init_db()
    employee_no = "MD-BAD-" + uuid4().hex[:8]
    with SessionLocal() as session:
        session.add(
            EmployeeRecord(
                employee_no=employee_no,
                source_employee_key="SRC-" + employee_no,
                national_id=str(uuid4().int)[-10:],
                first_name="Broken",
                last_name="Reference",
                employment_type="permanent",
                status="active",
                organization_unit_id="MISSING-ORG",
                position_id="MISSING-POS",
            )
        )
        session.commit()

    response = client.get("/api/v1/master-data/integrity")
    assert response.status_code == 200
    body = response.json()
    assert body["blocking"] is True
    codes = {item["code"] for item in body["findings"]}
    assert {"EMPLOYEE_ORG_MISSING", "EMPLOYEE_POSITION_MISSING"}.issubset(codes)


def test_masterdata_integrity_blocks_organization_cycles():
    init_db()
    with SessionLocal() as session:
        org = OrganizationUnitRecord(code="ORG-CYCLE-" + uuid4().hex[:8], name="Cycle", kind="district")
        session.add(org)
        session.flush()
        org.parent_id = org.id
        session.commit()
        code = org.code

    response = client.get("/api/v1/master-data/integrity")
    assert response.status_code == 200
    body = response.json()
    assert body["blocking"] is True
    assert any(item["code"] == "ORG_PARENT_CYCLE" and item["entity_id"] == code for item in body["findings"])
