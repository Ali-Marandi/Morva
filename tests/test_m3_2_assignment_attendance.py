from datetime import date
from decimal import Decimal
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from morva.persistence.domain_extensions import AttendanceFactRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import Base, EmployeeRecord
from morva.personnel.assignment_attendance import (
    approve_attendance_fact,
    register_assignment,
    register_attendance_fact,
    review_attendance_fact,
)


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _seed(session):
    org = OrganizationUnitRecord(code="ORG-M32", name="M3.2 Org", kind="school")
    position = PositionRecord(code="POS-M32", title="M3.2 Position", occupational_group="education")
    employee = EmployeeRecord(
        employee_no="M32-" + uuid4().hex[:8],
        source_employee_key="SRC-M32-" + uuid4().hex[:8],
        national_id=str(uuid4().int)[-10:],
        first_name="M3",
        last_name="Two",
        employment_type="permanent",
        status="active",
        organization_unit_id=org.code,
        position_id=position.code,
        hire_date=date(2020, 1, 1),
    )
    session.add_all([org, position, employee])
    session.commit()
    return employee


def test_assignment_is_reference_valid_idempotent_and_non_overlapping():
    with _session() as session:
        employee = _seed(session)
        first = register_assignment(
            session,
            employee_no=employee.employee_no,
            organization_code="ORG-M32",
            position_code="POS-M32",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 3, 31),
            acting=False,
            source_reference="ORDER-M32-1",
            source_hash="a" * 64,
            actor_id="importer",
        )
        session.commit()
        repeated = register_assignment(
            session,
            employee_no=employee.employee_no,
            organization_code="ORG-M32",
            position_code="POS-M32",
            starts_on=date(2026, 1, 1),
            ends_on=date(2026, 3, 31),
            acting=False,
            source_reference="ORDER-M32-1",
            source_hash="a" * 64,
            actor_id="importer",
        )
        assert repeated.status == "existing"
        assert repeated.assignment_id == first.assignment_id
        try:
            register_assignment(
                session,
                employee_no=employee.employee_no,
                organization_code="ORG-M32",
                position_code="POS-M32",
                starts_on=date(2026, 3, 1),
                ends_on=date(2026, 4, 30),
                acting=False,
                source_reference="ORDER-M32-2",
                source_hash="b" * 64,
                actor_id="importer",
            )
        except ValueError as exc:
            assert "overlaps" in str(exc)
        else:
            raise AssertionError("overlapping assignment must be rejected")


def test_attendance_lifecycle_is_received_reviewed_approved_with_distinct_actors():
    with _session() as session:
        employee = _seed(session)
        result = register_attendance_fact(
            session,
            employee_no=employee.employee_no,
            period="1405-06",
            source_record_key="ATT-M32-1",
            worked_units=Decimal("18"),
            leave_units=Decimal("1"),
            absence_units=Decimal("0"),
            source_hash="c" * 64,
            evidence={"source": "official-attendance"},
            actor_id="attendance-importer",
        )
        session.commit()
        record = review_attendance_fact(session, result.attendance_id, "attendance-reviewer")
        assert record.status == "reviewed"
        approved = approve_attendance_fact(session, record.id, "attendance-approver", "attendance-reviewer")
        assert approved.status == "approved"
        session.commit()

        stored = session.scalar(select(AttendanceFactRecord).where(AttendanceFactRecord.id == record.id))
        assert stored is not None
        assert stored.status == "approved"


def test_attendance_cannot_be_approved_by_same_reviewer():
    with _session() as session:
        employee = _seed(session)
        result = register_attendance_fact(
            session,
            employee_no=employee.employee_no,
            period="1405-06",
            source_record_key="ATT-M32-2",
            worked_units=Decimal("20"),
            leave_units=Decimal("0"),
            absence_units=Decimal("0"),
            source_hash="d" * 64,
            evidence={},
            actor_id="attendance-importer",
        )
        session.commit()
        review_attendance_fact(session, result.attendance_id, "same-user")
        try:
            approve_attendance_fact(session, result.attendance_id, "same-user", "same-user")
        except HTTPException as exc:
            assert exc.status_code == 409
            assert "distinct" in str(exc.detail)
        else:
            raise AssertionError("same reviewer and approver must be rejected")
