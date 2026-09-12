from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.masterdata.acceptance import (
    MasterDataAcceptanceRequest,
    assess_master_data_acceptance,
    confirm_master_data_acceptance,
)
from morva.persistence.acceptance_records import MasterDataAcceptanceRecord
from morva.persistence.database import init_db
from morva.persistence.domain_extensions import AssignmentRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import Base, EmployeeRecord, PersonnelSnapshotRecord


def _session():
    init_db()
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _coverage(
    *,
    organization_count=0,
    position_count=0,
    employee_count=0,
    assignment_count=0,
    personnel_snapshot_count=0,
    attendance_fact_count=0,
    teacher_rank_case_count=0,
):
    return {
        "organization_count": organization_count,
        "position_count": position_count,
        "employee_count": employee_count,
        "assignment_count": assignment_count,
        "personnel_snapshot_count": personnel_snapshot_count,
        "attendance_fact_count": attendance_fact_count,
        "teacher_rank_case_count": teacher_rank_case_count,
    }


def _request(**overrides):
    values = {
        "dataset_name": "education-masterdata",
        "schema_version": "1.0",
        "source_system": "official-source",
        "source_uri": "https://example.invalid/masterdata.csv",
        "authoritative_source_reference": "AUTH-REF-2026-001",
        "evidence_reference": "EVIDENCE-REF-2026-001",
        "evidence_sha256": "b" * 64,
        "population_scope": "test-population",
        "coverage_evidence": _coverage(),
        "dataset_period": "1405-06",
        "dataset_sha256": "a" * 64,
        "row_count": 1,
        "duplicate_key_count": 0,
        "rejected_row_count": 0,
        "schema_valid": True,
    }
    values.update(overrides)
    return MasterDataAcceptanceRequest(**values)


def _add_valid_master_data(session):
    org = OrganizationUnitRecord(code="ORG-" + uuid4().hex[:8], name="Test Org", kind="district")
    position = PositionRecord(
        code="POS-" + uuid4().hex[:8], title="Test Position", occupational_group="education"
    )
    session.add_all([org, position])
    session.flush()
    employee_no = "GOOD-" + uuid4().hex[:8]
    session.add(
        EmployeeRecord(
            employee_no=employee_no,
            source_employee_key="SRC-" + employee_no,
            national_id=str(uuid4().int)[-10:],
            first_name="Valid",
            last_name="Reference",
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
            effective_period="1405-06",
            effective_date=date(2026, 9, 1),
            organization_unit_id=str(org.id),
            position_id=position.code,
            employment_type="permanent",
            employment_status="active",
            source_hash="c" * 64,
            snapshot_hash="d" * 64,
            order_numbers=[],
            components={},
        )
    )
    session.commit()


def _valid_coverage():
    return _coverage(
        organization_count=1,
        position_count=1,
        employee_count=1,
        assignment_count=1,
        personnel_snapshot_count=1,
    )


def test_acceptance_blocks_invalid_manifest_contract():
    with _session() as session:
        result = assess_master_data_acceptance(
            session,
            _request(dataset_sha256="bad", duplicate_key_count=1, schema_valid=False),
            "acceptance-tester",
        )
        assert result.status == "blocked"
        assert result.eligible is False
        assert any("dataset_sha256" in item for item in result.blockers)
        assert any("duplicate_key_count" in item for item in result.blockers)
        assert any("schema_valid" in item for item in result.blockers)


def test_acceptance_requires_current_integrity_gate_to_be_clear():
    with _session() as session:
        session.add(
            EmployeeRecord(
                employee_no="BAD-" + uuid4().hex[:8],
                source_employee_key=None,
                national_id=str(uuid4().int)[-10:],
                first_name="Invalid",
                last_name="Reference",
                employment_type="permanent",
                status="active",
                organization_unit_id="MISSING-ORG",
                position_id="MISSING-POS",
                hire_date=date(2020, 1, 1),
            )
        )
        session.commit()
        result = assess_master_data_acceptance(
            session, _request(dataset_sha256="b" * 64), "acceptance-tester"
        )
        assert result.status == "blocked"
        assert result.integrity_blocking is True
        assert "current authoritative master-data integrity gate is blocking" in result.blockers


def test_acceptance_requires_evidence_coverage_to_match_persisted_population():
    with _session() as session:
        _add_valid_master_data(session)
        result = assess_master_data_acceptance(
            session,
            _request(dataset_sha256="c" * 64, coverage_evidence=_coverage()),
            "submitter",
        )
        assert result.status == "blocked"
        assert "coverage_evidence does not match persisted master-data population counts" in result.blockers


def test_acceptance_eligible_then_confirmed():
    with _session() as session:
        _add_valid_master_data(session)
        coverage = _valid_coverage()
        result = assess_master_data_acceptance(
            session, _request(dataset_sha256="e" * 64, coverage_evidence=coverage), "submitter"
        )
        assert result.status == "eligible"
        assert result.eligible is True
        assert result.blockers == ()
        assert len(result.evidence_fingerprint) == 64

        record = confirm_master_data_acceptance(
            session, result.acceptance_id, "approver", "FORMAL-AUTH-2026-001"
        )
        assert record.status == "accepted"
        assert record.accepted_by == "approver"
        assert record.authority_confirmation_reference == "FORMAL-AUTH-2026-001"
        assert len(record.integrity_snapshot_hash) == 64
        assert record.coverage_evidence == coverage
        assert len(record.evidence_fingerprint) == 64

        repeated = assess_master_data_acceptance(
            session,
            _request(dataset_sha256="E" * 64, coverage_evidence=coverage),
            "submitter",
        )
        assert repeated.status == "accepted"
        assert repeated.eligible is True
        assert repeated.acceptance_id == result.acceptance_id
        assert repeated.evidence_fingerprint == result.evidence_fingerprint


def test_acceptance_confirmation_requires_distinct_authority():
    with _session() as session:
        _add_valid_master_data(session)
        result = assess_master_data_acceptance(
            session, _request(dataset_sha256="1" * 64, coverage_evidence=_valid_coverage()), "submitter"
        )
        with pytest.raises(ValueError, match="distinct authority"):
            confirm_master_data_acceptance(
                session, result.acceptance_id, "submitter", "FORMAL-AUTH-2026-001"
            )


def test_acceptance_confirmation_rechecks_integrity():
    with _session() as session:
        _add_valid_master_data(session)
        result = assess_master_data_acceptance(
            session, _request(dataset_sha256="2" * 64, coverage_evidence=_valid_coverage()), "submitter"
        )
        employee = session.query(EmployeeRecord).filter(EmployeeRecord.employee_no.like("GOOD-%")).one()
        employee.organization_unit_id = "MISSING-ORG"
        session.commit()
        with pytest.raises(ValueError, match="integrity changed after assessment"):
            confirm_master_data_acceptance(
                session, result.acceptance_id, "approver", "FORMAL-AUTH-2026-002"
            )
        session.rollback()


def test_acceptance_confirmation_blocks_snapshot_drift_even_when_integrity_stays_valid():
    with _session() as session:
        _add_valid_master_data(session)
        result = assess_master_data_acceptance(
            session, _request(dataset_sha256="3" * 64, coverage_evidence=_valid_coverage()), "submitter"
        )
        employee = session.query(EmployeeRecord).filter(EmployeeRecord.employee_no.like("GOOD-%")).one()
        employee.first_name = "Changed"
        session.commit()
        with pytest.raises(ValueError, match="integrity snapshot changed after assessment"):
            confirm_master_data_acceptance(
                session, result.acceptance_id, "approver", "FORMAL-AUTH-2026-003"
            )
        session.rollback()


def test_acceptance_confirmation_blocks_tampered_evidence_fingerprint():
    with _session() as session:
        _add_valid_master_data(session)
        result = assess_master_data_acceptance(
            session, _request(dataset_sha256="4" * 64, coverage_evidence=_valid_coverage()), "submitter"
        )
        stored = session.get(MasterDataAcceptanceRecord, result.acceptance_id)
        stored.population_scope = "tampered-scope"
        session.commit()
        with pytest.raises(ValueError, match="evidence fingerprint changed"):
            confirm_master_data_acceptance(
                session, result.acceptance_id, "approver", "FORMAL-AUTH-2026-004"
            )
        session.rollback()


def test_acceptance_confirmation_cannot_bypass_blocker():
    with _session() as session:
        result = assess_master_data_acceptance(
            session, _request(dataset_sha256="f" * 64, rejected_row_count=2), "submitter"
        )
        try:
            confirm_master_data_acceptance(
                session, result.acceptance_id, "approver", "FORMAL-AUTH-2026-002"
            )
        except ValueError as exc:
            assert "blocked" in str(exc)
        else:
            raise AssertionError("blocked acceptance must not be confirmable")
