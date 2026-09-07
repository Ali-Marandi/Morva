from datetime import date
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.masterdata.authoritative import validate_authoritative_master_data
from morva.persistence.domain_extensions import AssignmentRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import Base, EmployeeRecord


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _employee(session, *, employee_no: str, org, position):
    session.add(
        EmployeeRecord(
            employee_no=employee_no,
            source_employee_key="SRC-" + employee_no,
            national_id=str(uuid4().int)[-10:],
            first_name="Authoritative",
            last_name="Test",
            employment_type="permanent",
            status="active",
            organization_unit_id=str(org.id),
            position_id=position.code,
            hire_date=date(2020, 1, 1),
        )
    )


def test_authoritative_gate_accepts_non_overlapping_assignments():
    with _session() as session:
        org = OrganizationUnitRecord(code="ORG-1", name="Org", kind="district")
        position = PositionRecord(code="POS-1", title="Position", occupational_group="education")
        session.add_all([org, position])
        session.flush()
        employee_no = "EMP-1"
        _employee(session, employee_no=employee_no, org=org, position=position)
        session.add_all(
            [
                AssignmentRecord(
                    employee_no=employee_no,
                    organization_code=org.code,
                    position_code=position.code,
                    starts_on=date(2026, 1, 1),
                    ends_on=date(2026, 3, 31),
                ),
                AssignmentRecord(
                    employee_no=employee_no,
                    organization_code=org.code,
                    position_code=position.code,
                    starts_on=date(2026, 4, 1),
                ),
            ]
        )
        session.commit()
        result = validate_authoritative_master_data(session)
        assert result.blocking is False
        assert result.findings == ()


def test_authoritative_gate_blocks_overlapping_assignments():
    with _session() as session:
        org = OrganizationUnitRecord(code="ORG-2", name="Org", kind="district")
        position = PositionRecord(code="POS-2", title="Position", occupational_group="education")
        session.add_all([org, position])
        session.flush()
        employee_no = "EMP-2"
        _employee(session, employee_no=employee_no, org=org, position=position)
        session.add_all(
            [
                AssignmentRecord(
                    employee_no=employee_no,
                    organization_code=org.code,
                    position_code=position.code,
                    starts_on=date(2026, 1, 1),
                    ends_on=date(2026, 6, 30),
                ),
                AssignmentRecord(
                    employee_no=employee_no,
                    organization_code=org.code,
                    position_code=position.code,
                    starts_on=date(2026, 6, 15),
                    ends_on=date(2026, 12, 31),
                ),
            ]
        )
        session.commit()
        result = validate_authoritative_master_data(session)
        assert result.blocking is True
        assert any(item.code == "ASSIGNMENT_OVERLAP" for item in result.findings)


def test_authoritative_gate_blocks_active_employee_without_assignment():
    with _session() as session:
        org = OrganizationUnitRecord(code="ORG-3", name="Org", kind="district")
        position = PositionRecord(code="POS-3", title="Position", occupational_group="education")
        session.add_all([org, position])
        session.flush()
        _employee(session, employee_no="EMP-3", org=org, position=position)
        session.commit()
        result = validate_authoritative_master_data(session)
        assert result.blocking is True
        assert any(item.code == "ACTIVE_EMPLOYEE_NO_ASSIGNMENT" for item in result.findings)


def test_authoritative_gate_blocks_invalid_position_effective_range():
    with _session() as session:
        org = OrganizationUnitRecord(code="ORG-4", name="Org", kind="district")
        position = PositionRecord(
            code="POS-4",
            title="Position",
            occupational_group="education",
            effective_from=date(2026, 6, 1),
            effective_to=date(2026, 5, 31),
        )
        session.add_all([org, position])
        session.flush()
        _employee(session, employee_no="EMP-4", org=org, position=position)
        session.commit()
        result = validate_authoritative_master_data(session)
        assert result.blocking is True
        assert any(item.code == "POSITION_INVALID_RANGE" for item in result.findings)
