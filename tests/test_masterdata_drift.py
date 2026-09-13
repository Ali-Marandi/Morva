from datetime import date
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.masterdata.acceptance import (
    MasterDataAcceptanceRequest,
    assess_master_data_acceptance,
    confirm_master_data_acceptance,
)
from morva.masterdata.drift import detect_master_data_drift
from morva.persistence.acceptance_records import MasterDataAcceptanceRecord
from morva.persistence.domain_extensions import AssignmentRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import Base, EmployeeRecord, PersonnelSnapshotRecord


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return factory()


def _coverage(**overrides):
    values = {
        "organization_count": 1,
        "position_count": 1,
        "employee_count": 1,
        "assignment_count": 1,
        "personnel_snapshot_count": 1,
        "attendance_fact_count": 0,
        "teacher_rank_case_count": 0,
    }
    values.update(overrides)
    return values


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


def _accept(session):
    _add_valid_master_data(session)
    payload = MasterDataAcceptanceRequest(
        dataset_name="education-masterdata",
        schema_version="1.0",
        source_system="official-source",
        source_uri="https://example.invalid/masterdata.csv",
        authoritative_source_reference="AUTH-REF-2026-001",
        evidence_reference="EVIDENCE-REF-2026-001",
        evidence_sha256="b" * 64,
        population_scope="test-population",
        coverage_evidence=_coverage(),
        dataset_period="1405-06",
        dataset_sha256="a" * 64,
        row_count=1,
        duplicate_key_count=0,
        rejected_row_count=0,
        schema_valid=True,
    )
    result = assess_master_data_acceptance(session, payload, "submitter")
    assert result.eligible is True
    confirm_master_data_acceptance(session, result.acceptance_id, "approver", "FORMAL-AUTH-2026-001")
    return result.acceptance_id


def test_drift_is_clean_for_unchanged_accepted_dataset():
    with _session() as session:
        acceptance_id = _accept(session)
        result = detect_master_data_drift(session, acceptance_id)
        assert result.detected is False
        assert result.blockers == ()
        assert all(delta == 0 for delta in result.coverage_deltas.values())
        assert result.current_integrity_snapshot_hash == result.accepted_integrity_snapshot_hash


def test_drift_detects_content_change_with_stable_population_counts():
    with _session() as session:
        acceptance_id = _accept(session)
        employee = (
            session.query(EmployeeRecord)
            .filter(EmployeeRecord.employee_no.like("GOOD-%"))
            .one()
        )
        employee.first_name = "Changed"
        session.commit()
        result = detect_master_data_drift(session, acceptance_id)
        assert result.detected is True
        assert "master-data integrity snapshot differs from accepted evidence" in result.blockers
        assert result.coverage_deltas["employee_count"] == 0


def test_drift_reports_population_count_change():
    with _session() as session:
        acceptance_id = _accept(session)
        session.add(
            OrganizationUnitRecord(
                code="ORG-DRIFT-" + uuid4().hex[:8], name="New Org", kind="district"
            )
        )
        session.commit()
        result = detect_master_data_drift(session, acceptance_id)
        assert result.detected is True
        assert result.coverage_deltas["organization_count"] == 1
        assert "master-data population coverage differs from accepted evidence" in result.blockers


def test_drift_fails_closed_for_unknown_acceptance():
    with _session() as session:
        with pytest.raises(ValueError, match="not found"):
            detect_master_data_drift(session, uuid4())


def test_drift_detects_tampered_acceptance_metadata():
    with _session() as session:
        acceptance_id = _accept(session)
        record = session.get(MasterDataAcceptanceRecord, uuid4())
        assert record is None
        record = session.get(MasterDataAcceptanceRecord, UUID(acceptance_id))
        record.population_scope = "tampered"
        session.commit()
        result = detect_master_data_drift(session, acceptance_id)
        assert result.detected is True
        assert "accepted master-data evidence fingerprint is inconsistent" in result.blockers
