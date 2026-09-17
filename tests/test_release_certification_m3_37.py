from datetime import datetime, timezone

import pytest

from morva.runtime.release_certification import (
    CertificationSignoff,
    ReleaseCertification,
    ReleaseCertificationError,
)


NOW = datetime(2026, 9, 17, 17, 0, tzinfo=timezone.utc)
REQUIRED = ("security-report", "dr-evidence", "load-evidence", "reconciliation-evidence")


def signoffs() -> tuple[CertificationSignoff, ...]:
    return (
        CertificationSignoff("finance", "finance-approver", NOW, "evidence://finance"),
        CertificationSignoff("legal", "legal-approver", NOW, "evidence://legal"),
        CertificationSignoff("operations", "ops-approver", NOW, "evidence://operations"),
    )


def test_release_certification_is_not_ready_without_required_evidence():
    certification = ReleaseCertification(
        release_id="morva-1.0.1",
        candidate_sha="a" * 40,
        required_evidence=REQUIRED,
        verified_evidence=REQUIRED[:-1],
        security_signoff_complete=True,
        disaster_recovery_signoff_complete=True,
        load_signoff_complete=True,
        reconciliation_signoff_complete=True,
        signoffs=signoffs(),
    )

    assert certification.release_ready is False
    with pytest.raises(ReleaseCertificationError, match="missing certification evidence"):
        certification.assert_release_ready()


def test_release_certification_requires_all_formal_signoffs_and_domains():
    certification = ReleaseCertification(
        release_id="morva-1.0.1",
        candidate_sha="b" * 40,
        required_evidence=REQUIRED,
        verified_evidence=REQUIRED,
    )

    assert certification.release_ready is False
    assert certification.missing_signoffs == ("finance", "legal", "operations")
    with pytest.raises(ReleaseCertificationError, match="missing certification signoffs"):
        certification.assert_release_ready()


def test_release_certification_happy_path_is_deterministic():
    certification = ReleaseCertification(
        release_id="morva-1.0.1",
        candidate_sha="c" * 40,
        required_evidence=REQUIRED,
        verified_evidence=REQUIRED,
        security_signoff_complete=True,
        disaster_recovery_signoff_complete=True,
        load_signoff_complete=True,
        reconciliation_signoff_complete=True,
        signoffs=signoffs(),
    )

    assert certification.release_ready is True
    certification.assert_release_ready()
    assert certification.fingerprint == certification.fingerprint


def test_release_certification_rejects_invalid_commit_or_duplicate_roles():
    with pytest.raises(ReleaseCertificationError, match="candidate_sha"):
        ReleaseCertification(
            release_id="morva-1.0.1",
            candidate_sha="not-a-sha",
            required_evidence=REQUIRED,
            verified_evidence=REQUIRED,
        )

    duplicate = signoffs() + (
        CertificationSignoff("finance", "finance-2", NOW, "evidence://finance-2"),
    )
    with pytest.raises(ReleaseCertificationError, match="each certification role"):
        ReleaseCertification(
            release_id="morva-1.0.1",
            candidate_sha="d" * 40,
            required_evidence=REQUIRED,
            verified_evidence=REQUIRED,
            signoffs=duplicate,
        )


def test_signoff_requires_timezone_aware_timestamp():
    with pytest.raises(ReleaseCertificationError, match="timezone-aware"):
        CertificationSignoff("finance", "finance", datetime(2026, 9, 17), "evidence://finance")
