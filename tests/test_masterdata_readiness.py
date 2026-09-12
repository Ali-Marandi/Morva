from uuid import UUID

import pytest

from morva.masterdata.acceptance import assess_master_data_acceptance, confirm_master_data_acceptance
from morva.masterdata.readiness import verify_master_data_readiness
from morva.persistence.acceptance_records import MasterDataAcceptanceRecord
from morva.persistence.models import EmployeeRecord

from test_masterdata_acceptance import _add_valid_master_data, _request, _session, _valid_coverage


def test_readiness_fails_closed_without_accepted_assessment():
    with _session() as session:
        result = verify_master_data_readiness(session)
        assert result.ready is False
        assert result.blockers == ("no accepted master-data assessment is available",)


def test_readiness_accepts_an_unchanged_authoritative_assessment():
    with _session() as session:
        _add_valid_master_data(session)
        coverage = _valid_coverage()
        assessed = assess_master_data_acceptance(
            session, _request(dataset_sha256="8" * 64, coverage_evidence=coverage), "submitter"
        )
        confirm_master_data_acceptance(session, assessed.acceptance_id, "authority", "FORMAL-AUTH-2026-008")

        result = verify_master_data_readiness(session, dataset_name="education-masterdata")
        assert result.ready is True
        assert result.acceptance_id == assessed.acceptance_id
        assert result.dataset_sha256 == "8" * 64
        assert len(result.integrity_snapshot_hash or "") == 64


def test_readiness_blocks_after_master_data_changes():
    with _session() as session:
        _add_valid_master_data(session)
        coverage = _valid_coverage()
        assessed = assess_master_data_acceptance(
            session, _request(dataset_sha256="9" * 64, coverage_evidence=coverage), "submitter"
        )
        confirm_master_data_acceptance(session, assessed.acceptance_id, "authority", "FORMAL-AUTH-2026-009")

        employee = session.query(EmployeeRecord).filter(EmployeeRecord.employee_no.like("GOOD-%")).one()
        employee.first_name = "Drifted"
        session.commit()

        result = verify_master_data_readiness(session)
        assert result.ready is False
        assert "master-data integrity snapshot differs from accepted evidence" in result.blockers


def test_readiness_blocks_tampered_acceptance_record():
    with _session() as session:
        _add_valid_master_data(session)
        coverage = _valid_coverage()
        assessed = assess_master_data_acceptance(
            session, _request(dataset_sha256="a" * 64, coverage_evidence=coverage), "submitter"
        )
        confirm_master_data_acceptance(session, assessed.acceptance_id, "authority", "FORMAL-AUTH-2026-010")

        record = session.get(MasterDataAcceptanceRecord, UUID(assessed.acceptance_id))
        assert record is not None
        record.population_scope = "tampered"
        session.commit()

        result = verify_master_data_readiness(session)
        assert result.ready is False
        assert "accepted master-data evidence fingerprint is inconsistent" in result.blockers


def test_readiness_can_target_exact_dataset_hash():
    with _session() as session:
        _add_valid_master_data(session)
        coverage = _valid_coverage()
        assessed = assess_master_data_acceptance(
            session, _request(dataset_sha256="b" * 64, coverage_evidence=coverage), "submitter"
        )
        confirm_master_data_acceptance(session, assessed.acceptance_id, "authority", "FORMAL-AUTH-2026-011")

        result = verify_master_data_readiness(
            session, dataset_name="education-masterdata", dataset_sha256="c" * 64
        )
        assert result.ready is False
        assert result.acceptance_id is None


if __name__ == "__main__":
    pytest.main()
