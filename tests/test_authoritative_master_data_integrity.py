from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.hr.teacher_rank_decision_integrity import (
    canonical_teacher_rank_decision_payload,
    teacher_rank_decision_fingerprint,
)
from morva.masterdata.authoritative import validate_authoritative_master_data
from morva.persistence.database import init_db
from morva.persistence.domain_extensions import AssignmentRecord, AttendanceFactRecord, TeacherRankCaseRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import Base, EmployeeRecord


def _session():
    init_db()
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _employee_fixture(session):
    org = OrganizationUnitRecord(code="ORG-" + uuid4().hex[:8], name="Test Org", kind="district")
    position = PositionRecord(code="POS-" + uuid4().hex[:8], title="Teacher", occupational_group="education")
    session.add_all([org, position])
    session.flush()
    employee_no = "MD-" + uuid4().hex[:8]
    employee = EmployeeRecord(
        employee_no=employee_no,
        source_employee_key="SRC-" + employee_no,
        national_id=str(uuid4().int)[-10:],
        first_name="Test",
        last_name="Teacher",
        employment_type="permanent",
        status="active",
        organization_unit_id=str(org.id),
        position_id=position.code,
        hire_date=date(2020, 1, 1),
    )
    session.add(employee)
    session.add(
        AssignmentRecord(
            employee_no=employee_no,
            organization_code=org.code,
            position_code=position.code,
            starts_on=date(2026, 1, 1),
        )
    )
    session.flush()
    return employee_no, org, position


def test_authoritative_gate_accepts_valid_attendance():
    with _session() as session:
        employee_no, _, _ = _employee_fixture(session)
        session.add(
            AttendanceFactRecord(
                employee_no=employee_no,
                period="2026-08",
                source_record_key="ATT-1",
                worked_units=Decimal("20"),
                leave_units=Decimal("0"),
                absence_units=Decimal("0"),
                status="received",
                source_hash="a" * 64,
                evidence={"source": "authoritative-feed"},
            )
        )
        session.commit()

        result = validate_authoritative_master_data(session)
        assert result.blocking is False
        assert result.findings == ()


def test_authoritative_gate_blocks_invalid_attendance():
    with _session() as session:
        _employee_fixture(session)
        session.add(
            AttendanceFactRecord(
                employee_no="MISSING-EMPLOYEE",
                period="2026-13",
                source_record_key="ATT-INVALID",
                worked_units=Decimal("-1"),
                leave_units=Decimal("0"),
                absence_units=Decimal("0"),
                status="unknown",
                source_hash="not-a-sha",
                evidence={},
            )
        )
        session.commit()

        result = validate_authoritative_master_data(session)
        codes = {item.code for item in result.findings}
        assert result.blocking is True
        assert {
            "ATTENDANCE_EMPLOYEE_MISSING",
            "ATTENDANCE_INVALID_PERIOD",
            "ATTENDANCE_INVALID_STATUS",
            "ATTENDANCE_NEGATIVE_UNITS",
            "ATTENDANCE_SOURCE_HASH_INVALID",
        }.issubset(codes)


def test_authoritative_gate_blocks_tampered_persisted_rank_decision():
    with _session() as session:
        employee_no, _, _ = _employee_fixture(session)
        case = TeacherRankCaseRecord(
            employee_no=employee_no,
            proposed_rank="مربی معلم",
            status="decided",
            effect_period="2026-08",
            decision_reference="DEC-1",
            committee_payload={"_governance": {"actor_id": "approver", "reviewer_id": "reviewer"}},
        )
        session.add(case)
        session.flush()
        payload = canonical_teacher_rank_decision_payload(
            case_id=str(case.id),
            employee_no=employee_no,
            proposed_rank=case.proposed_rank,
            effect_period=case.effect_period,
            decision_reference=case.decision_reference,
            committee_governance={"actor_id": "approver", "reviewer_id": "reviewer"},
            evidence_fingerprint="evidence:legal-source",
        )
        case.committee_payload = {
            "_governance": {"actor_id": "approver", "reviewer_id": "reviewer"},
            "_decision_provenance": {
                "fingerprint": teacher_rank_decision_fingerprint(payload),
                "payload": {**payload, "decision_reference": "TAMPERED"},
            },
        }
        session.commit()

        result = validate_authoritative_master_data(session)
        assert result.blocking is True
        assert any(item.code == "RANK_DECISION_PROVENANCE_INVALID" for item in result.findings)


def test_authoritative_gate_blocks_inactive_assignment_targets():
    with _session() as session:
        employee_no, org, position = _employee_fixture(session)
        org.active = False
        position.active = False
        session.commit()

        result = validate_authoritative_master_data(session)
        codes = {item.code for item in result.findings}
        assert result.blocking is True
        assert {"ASSIGNMENT_ORG_INACTIVE", "ASSIGNMENT_POSITION_INACTIVE"}.issubset(codes)


def test_authoritative_gate_blocks_multiple_open_assignments():
    with _session() as session:
        employee_no, org, position = _employee_fixture(session)
        session.add(
            AssignmentRecord(
                employee_no=employee_no,
                organization_code=org.code,
                position_code=position.code,
                starts_on=date(2026, 2, 1),
            )
        )
        session.commit()

        result = validate_authoritative_master_data(session)
        assert result.blocking is True
        assert any(item.code == "ACTIVE_EMPLOYEE_MULTIPLE_ASSIGNMENTS" for item in result.findings)
