from datetime import date, datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.masterdata.acceptance import MasterDataAcceptanceRequest, assess_master_data_acceptance, confirm_master_data_acceptance
from morva.masterdata.authoritative_attestation import (
    MasterDataAuthorityAttestation,
    assess_authoritative_master_data_attestation,
)
from morva.persistence.domain_extensions import AssignmentRecord
from morva.persistence.enterprise_models import OrganizationUnitRecord
from morva.persistence.masterdata_records import PositionRecord
from morva.persistence.models import Base, EmployeeRecord, PersonnelSnapshotRecord


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _coverage():
    return {
        "organization_count": 1,
        "position_count": 1,
        "employee_count": 1,
        "assignment_count": 1,
        "personnel_snapshot_count": 1,
        "attendance_fact_count": 0,
        "teacher_rank_case_count": 0,
    }


def _add_valid_master_data(session):
    org = OrganizationUnitRecord(code="ORG-" + uuid4().hex[:8], name="Test Org", kind="district")
    position = PositionRecord(code="POS-" + uuid4().hex[:8], title="Test Position", occupational_group="education")
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


def _accepted_assessment(session):
    _add_valid_master_data(session)
    request = MasterDataAcceptanceRequest(
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
    result = assess_master_data_acceptance(session, request, "submitter")
    assert result.eligible is True
    record = confirm_master_data_acceptance(session, result.acceptance_id, "confirmer", "FORMAL-AUTH-2026-001")
    assert record.status == "accepted"
    return record


def _attestation(record, **overrides):
    values = {
        "acceptance_id": record.id,
        "authority_reference": "POPULATION-ATTEST-2026-001",
        "authority_actor_id": "population-authority",
        "attested_at": datetime(2026, 9, 14, 0, 0, tzinfo=timezone.utc),
        "expected_coverage": _coverage(),
        "complete_dimensions": (
            "organization_count",
            "position_count",
            "employee_count",
            "assignment_count",
            "personnel_snapshot_count",
            "attendance_fact_count",
            "teacher_rank_case_count",
        ),
    }
    values.update(overrides)
    return MasterDataAuthorityAttestation(**values)


def test_attestation_accepts_exact_complete_population_evidence():
    with _session() as session:
        record = _accepted_assessment(session)
        result = assess_authoritative_master_data_attestation(session, _attestation(record))
        assert result.eligible is True
        assert result.blockers == ()
        assert len(result.attestation_fingerprint) == 64


def test_attestation_blocks_population_count_drift():
    with _session() as session:
        record = _accepted_assessment(session)
        coverage = _coverage()
        coverage["employee_count"] = 2
        result = assess_authoritative_master_data_attestation(session, _attestation(record, expected_coverage=coverage))
        assert result.eligible is False
        assert any("employee_count" in item and "does not match persisted count" in item for item in result.blockers)


def test_attestation_requires_all_dimensions_to_be_explicitly_attested():
    with _session() as session:
        record = _accepted_assessment(session)
        complete = tuple(item for item in _attestation(record).complete_dimensions if item != "attendance_fact_count")
        result = assess_authoritative_master_data_attestation(session, _attestation(record, complete_dimensions=complete))
        assert result.eligible is False
        assert "complete_dimensions.attendance_fact_count must be explicitly attested" in result.blockers


def test_attestation_enforces_separation_of_duties_and_accepted_state():
    with _session() as session:
        record = _accepted_assessment(session)
        result = assess_authoritative_master_data_attestation(session, _attestation(record, authority_actor_id="submitter"))
        assert result.eligible is False
        assert "authority attestor must differ from dataset submitter" in result.blockers

        result = assess_authoritative_master_data_attestation(session, _attestation(record, authority_actor_id="confirmer"))
        assert result.eligible is False
        assert "authority attestor must differ from acceptance confirmer" in result.blockers

        record.status = "eligible"
        session.commit()
        result = assess_authoritative_master_data_attestation(session, _attestation(record))
        assert result.eligible is False
        assert "master-data acceptance must be accepted before authority attestation" in result.blockers


def test_attestation_requires_timezone_aware_timestamp():
    with _session() as session:
        record = _accepted_assessment(session)
        result = assess_authoritative_master_data_attestation(
            session, _attestation(record, attested_at=datetime(2026, 9, 14))
        )
        assert result.eligible is False
        assert "attested_at must be timezone-aware" in result.blockers
