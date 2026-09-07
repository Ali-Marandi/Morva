from datetime import date
from uuid import uuid4

from fastapi.testclient import TestClient

from morva.api.app import app
from morva.persistence.core_hr_employment import EmploymentRecord
from morva.persistence.core_hr_records import DependentRecord, EducationRecord, ExperienceRecord
from morva.persistence.database import SessionLocal, init_db
from morva.persistence.domain_extensions import AssignmentRecord
from morva.persistence.models import EmployeeRecord, PersonnelSnapshotRecord
from morva.security.auth import get_current_principal
from morva.security.policy import Principal, Scope


app.dependency_overrides[get_current_principal] = lambda: Principal(
    user_id="test-admin",
    role="admin",
    scope=Scope.MINISTRY,
    scope_id="ministry",
    mfa_verified=True,
)
client = TestClient(app)


def _seed_employee() -> str:
    init_db()
    employee_no = "HR-" + uuid4().hex[:10]
    national_id = str(uuid4().int)[-10:]
    with SessionLocal() as session:
        session.add(
            EmployeeRecord(
                employee_no=employee_no,
                source_employee_key="SRC-" + employee_no,
                national_id=national_id,
                first_name="Test",
                last_name="Employee",
                employment_type="permanent",
                status="active",
                organization_unit_id="ORG-TEST",
                position_id="POS-TEST",
                hire_date=date(2020, 1, 1),
            )
        )
        session.add(
            EmploymentRecord(
                employee_no=employee_no,
                employment_type="permanent",
                organization_unit_id="ORG-TEST",
                position_id="POS-TEST",
                starts_on=date(2020, 1, 1),
                status="active",
            )
        )
        session.add(
            AssignmentRecord(
                employee_no=employee_no,
                organization_code="ORG-TEST",
                position_code="POS-TEST",
                starts_on=date(2020, 1, 1),
                acting=False,
            )
        )
        session.add(
            EducationRecord(
                employee_no=employee_no,
                level="bachelor",
                field_of_study="education",
                institution="Test University",
                completed_on=date(2019, 6, 1),
            )
        )
        session.add_all(
            [
                ExperienceRecord(
                    employee_no=employee_no,
                    experience_type="ministry",
                    organization_name="Old Ministry",
                    starts_on=date(2018, 1, 1),
                    ends_on=date(2019, 12, 31),
                ),
                ExperienceRecord(
                    employee_no=employee_no,
                    experience_type="teaching",
                    organization_name="Current School",
                    starts_on=date(2020, 1, 1),
                ),
            ]
        )
        session.add_all(
            [
                DependentRecord(
                    employee_no=employee_no,
                    relationship="child",
                    name="Child One",
                    birth_date=date(2016, 1, 1),
                    valid_from=date(2020, 1, 1),
                    valid_to=date(2035, 12, 31),
                ),
                DependentRecord(
                    employee_no=employee_no,
                    relationship="spouse",
                    name="Spouse One",
                    valid_from=date(2020, 1, 1),
                    valid_to=None,
                ),
            ]
        )
        session.commit()
    return employee_no


def test_employee_profile_returns_core_hr_chain():
    employee_no = _seed_employee()
    response = client.get(f"/api/v1/hr/employees/{employee_no}/profile", params={"effective_on": "2024-01-01"})
    assert response.status_code == 200
    body = response.json()
    assert body["employee"]["employee_no"] == employee_no
    assert body["effective_employment"]["position_id"] == "POS-TEST"
    assert body["effective_assignment"]["position_code"] == "POS-TEST"
    assert len(body["education"]) == 1
    assert len(body["experience"]) == 1
    assert len(body["dependents"]) == 2


def test_experience_effective_date_filters_history():
    employee_no = _seed_employee()
    response = client.get(
        f"/api/v1/hr/employees/{employee_no}/experience",
        params={"effective_on": "2019-06-01"},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["organization_name"] for item in items] == ["Old Ministry"]


def test_dependents_effective_date_filters_validity_window():
    employee_no = _seed_employee()
    response = client.get(
        f"/api/v1/hr/employees/{employee_no}/dependents",
        params={"effective_on": "2040-01-01"},
    )
    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == ["Spouse One"]


def test_snapshot_is_idempotent_and_readable():
    employee_no = _seed_employee()
    first = client.post(
        f"/api/v1/hr/employees/{employee_no}/snapshots",
        params={"effective_on": "2024-01-15", "effective_period": "2024-01"},
    )
    second = client.post(
        f"/api/v1/hr/employees/{employee_no}/snapshots",
        params={"effective_on": "2024-01-15", "effective_period": "2024-01"},
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["snapshot_hash"] == first.json()["snapshot_hash"]

    fetched = client.get(f"/api/v1/hr/employees/{employee_no}/snapshots/2024-01")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == first.json()["id"]
    assert fetched.json()["components"]["core_hr"]["resolved"]["position_id"] == "POS-TEST"


def test_snapshot_rejects_content_change_after_creation():
    employee_no = _seed_employee()
    created = client.post(
        f"/api/v1/hr/employees/{employee_no}/snapshots",
        params={"effective_on": "2024-01-15", "effective_period": "2024-01"},
    )
    assert created.status_code == 201
    with SessionLocal() as session:
        employee = session.scalar(select(EmployeeRecord).where(EmployeeRecord.employee_no == employee_no))
        employee.last_name = "Changed"
        session.commit()

    conflict = client.post(
        f"/api/v1/hr/employees/{employee_no}/snapshots",
        params={"effective_on": "2024-01-15", "effective_period": "2024-01"},
    )
    assert conflict.status_code == 409


def test_snapshot_rejects_mismatched_period():
    employee_no = _seed_employee()
    response = client.post(
        f"/api/v1/hr/employees/{employee_no}/snapshots",
        params={"effective_on": "2024-01-15", "effective_period": "2024-02"},
    )
    assert response.status_code == 422


def test_snapshot_requires_personnel_write_permission():
    employee_no = _seed_employee()
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        user_id="test-finance",
        role="school_finance",
        scope=Scope.SCHOOL,
        scope_id="ORG-TEST",
        mfa_verified=True,
    )
    try:
        response = client.post(
            f"/api/v1/hr/employees/{employee_no}/snapshots",
            params={"effective_on": "2024-01-15", "effective_period": "2024-01"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides[get_current_principal] = lambda: Principal(
            user_id="test-admin",
            role="admin",
            scope=Scope.MINISTRY,
            scope_id="ministry",
            mfa_verified=True,
        )
