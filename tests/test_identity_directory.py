from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.persistence.models import Base, EmployeeRecord
from morva.security.identity_directory import reconcile_employee_identity


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def _employee(employee_no: str, source_key: str | None = None) -> EmployeeRecord:
    from uuid import uuid4

    return EmployeeRecord(
        id=uuid4(),
        employee_no=employee_no,
        source_employee_key=source_key,
        national_id=f"N-{employee_no}",
        first_name="Test",
        last_name="Employee",
        employment_type="employee",
        status="active",
        organization_unit_id="ORG-1",
        position_id="POS-1",
    )


def test_reconcile_matches_canonical_employee_number() -> None:
    with _session() as session:
        employee = _employee("EMP-001", "SRC-001")
        session.add(employee)
        session.commit()

        result = reconcile_employee_identity(session, " EMP-001 ")

        assert result.resolved
        assert result.employee is employee
        assert result.match_type == "employee_no"
        assert result.candidate_employee_nos == ("EMP-001",)


def test_reconcile_matches_immutable_source_employee_key() -> None:
    with _session() as session:
        employee = _employee("EMP-001", "SRC-001")
        session.add(employee)
        session.commit()

        result = reconcile_employee_identity(session, "SRC-001")

        assert result.resolved
        assert result.employee is employee
        assert result.match_type == "source_employee_key"


def test_reconcile_fails_closed_for_multiple_distinct_records() -> None:
    with _session() as session:
        first = _employee("EMP-001", "FED-001")
        second = _employee("EMP-002", "FED-002")
        session.add_all([first, second])
        session.commit()

        second.source_employee_key = "EMP-001"
        session.commit()

        result = reconcile_employee_identity(session, "EMP-001")

        assert not result.resolved
        assert result.ambiguous
        assert result.candidate_employee_nos == ("EMP-001", "EMP-002")
        assert result.reason == "identity maps to multiple employee records"


def test_reconcile_reports_unmapped_identity_without_mutation() -> None:
    with _session() as session:
        employee = _employee("EMP-001", "SRC-001")
        session.add(employee)
        session.commit()

        result = reconcile_employee_identity(session, "UNKNOWN")

        assert not result.resolved
        assert not result.ambiguous
        assert result.candidate_employee_nos == ()
        assert result.reason == "identity is not mapped to the employee directory"
        assert session.query(EmployeeRecord).count() == 1
