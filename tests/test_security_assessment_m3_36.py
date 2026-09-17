from datetime import datetime, timezone
from hashlib import sha256

import pytest

from morva.runtime.security_assessment import (
    SecurityAssessment,
    SecurityAssessmentError,
    SecurityFinding,
)


NOW = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
SCOPE_HASH = sha256(b"morva-m3-36-scope").hexdigest()
CONTROLS = (
    "authentication",
    "authorization",
    "cryptography",
    "auditability",
    "supply_chain",
    "secrets",
    "availability",
)


def assessment(**overrides) -> SecurityAssessment:
    values = {
        "assessment_id": "M3.36-PREFLIGHT-1",
        "assessed_at": NOW,
        "scope_hash": SCOPE_HASH,
        "required_controls": CONTROLS,
        "verified_controls": CONTROLS,
    }
    values.update(overrides)
    return SecurityAssessment(**values)


def test_pre_assessment_record_is_not_release_ready_without_independent_signoff():
    record = assessment()

    assert record.release_ready is False
    with pytest.raises(SecurityAssessmentError, match="independent security signoff"):
        record.assert_release_ready()


def test_release_ready_requires_all_controls_and_signed_external_report():
    record = assessment(
        independent_assessor="independent-security-firm",
        independent_report_uri="evidence://security/M3.36/report",
        independent_signed_at=NOW,
    )

    assert record.release_ready is True
    record.assert_release_ready()


def test_open_critical_and_high_findings_are_blocking():
    record = assessment(
        findings=(
            SecurityFinding("SEC-001", "critical", "open"),
            SecurityFinding("SEC-002", "high", "open"),
            SecurityFinding("SEC-003", "medium", "open"),
        ),
        independent_assessor="independent-security-firm",
        independent_report_uri="evidence://security/M3.36/report",
        independent_signed_at=NOW,
    )

    assert [item.finding_id for item in record.open_critical_or_high] == ["SEC-001", "SEC-002"]
    assert record.release_ready is False
    with pytest.raises(SecurityAssessmentError, match="critical/high"):
        record.assert_release_ready()


def test_missing_control_is_blocking_even_with_signed_report():
    record = assessment(
        verified_controls=CONTROLS[:-1],
        independent_assessor="independent-security-firm",
        independent_report_uri="evidence://security/M3.36/report",
        independent_signed_at=NOW,
    )

    assert record.missing_controls == ("availability",)
    assert record.release_ready is False
    with pytest.raises(SecurityAssessmentError, match="availability"):
        record.assert_release_ready()


def test_findings_must_use_supported_values():
    with pytest.raises(SecurityAssessmentError, match="unsupported finding severity"):
        SecurityFinding("SEC-001", "urgent", "open")
    with pytest.raises(SecurityAssessmentError, match="unsupported finding status"):
        SecurityFinding("SEC-001", "high", "accepted")


def test_assessment_fingerprint_is_deterministic():
    first = assessment(
        findings=(SecurityFinding("SEC-010", "low", "remediated"),),
    )
    second = assessment(
        findings=(SecurityFinding("SEC-010", "low", "remediated"),),
    )

    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64


def test_timestamps_must_be_timezone_aware():
    with pytest.raises(SecurityAssessmentError, match="timezone-aware"):
        assessment(assessed_at=datetime(2026, 9, 17, 12, 0))

    with pytest.raises(SecurityAssessmentError, match="timezone-aware"):
        assessment(independent_signed_at=datetime(2026, 9, 17, 12, 0))
