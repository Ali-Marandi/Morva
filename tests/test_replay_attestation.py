from datetime import datetime, timezone

import pytest

from morva.payroll.replay_attestation import ReplayCertificationRequest


FINGERPRINT = "a" * 64


def _request(**overrides: object) -> ReplayCertificationRequest:
    values = dict(
        artifact_id="artifact-001",
        period="1405-01",
        personnel_snapshot_id="snapshot-001",
        personnel_snapshot_hash=FINGERPRINT,
        rule_pack_version="1405.1",
        rule_pack_hash=FINGERPRINT,
        input_hash=FINGERPRINT,
        expected_output_hash=FINGERPRINT,
        replay_output_hash=FINGERPRINT,
        replay_fingerprint=FINGERPRINT,
        certified_at=datetime(2026, 3, 22, 12, tzinfo=timezone.utc),
        reviewer_id="legal-reviewer",
        approver_id="finance-approver",
        status="review_required",
    )
    values.update(overrides)
    return ReplayCertificationRequest(**values)


def test_review_required_is_never_execution_ready():
    request = _request()
    request.validate()
    assert not request.execution_ready()


def test_certification_requires_exact_replayed_output_hash():
    request = _request(status="certified", replay_output_hash="b" * 64)

    assert not request.execution_ready()


def test_certified_matching_replay_is_execution_ready():
    request = _request(status="certified")

    assert request.execution_ready()


def test_replay_certification_requires_timezone_aware_timestamp():
    request = _request(certified_at=datetime(2026, 3, 22, 12))

    with pytest.raises(ValueError, match="certified_at must be timezone-aware"):
        request.validate()


def test_replay_certification_requires_independent_review_and_approval():
    request = _request(reviewer_id="same-user", approver_id="same-user")

    with pytest.raises(ValueError, match="reviewer and approver must be distinct"):
        request.validate()


def test_replay_certification_rejects_malformed_sha256_fields():
    request = _request(input_hash="not-a-sha256")

    with pytest.raises(ValueError, match="input_hash must be a 64-character SHA-256 hex digest"):
        request.validate()


def test_certification_fingerprint_is_deterministic():
    first = _request(status="certified")
    second = _request(status="certified")

    assert first.certification_fingerprint() == second.certification_fingerprint()
