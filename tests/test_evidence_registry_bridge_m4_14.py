from __future__ import annotations

from datetime import datetime, timezone

import pytest

from morva.persistence.evidence_submission_records import (
    AuthoritativeEvidenceSubmissionRecord,
)
from morva.runtime.evidence_registry_bridge import (
    EvidenceRegistryBridgeError,
    build_registry_projection,
    submission_to_authoritative_item,
)
from morva.security.policy import Scope


NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)


def _record(
    *,
    evidence_id: str,
    status: str = "accepted",
    source_type: str = "legal_rule",
    source_uri: str = "https://authority.example/evidence/1",
    submitted_by: str = "submitter",
    decided_by: str | None = "approver",
) -> AuthoritativeEvidenceSubmissionRecord:
    record = AuthoritativeEvidenceSubmissionRecord(
        evidence_id=evidence_id,
        source_type=source_type,
        source_uri=source_uri,
        source_sha256="a" * 64,
        issuer="authority",
        population_scope="teachers",
        submission_scope=Scope.PROVINCE.value,
        submission_scope_id="province-1",
        effective_from=NOW,
        effective_to=datetime(2027, 1, 1, tzinfo=timezone.utc),
        expires_at=datetime(2026, 12, 31, tzinfo=timezone.utc),
        status=status,
        submitted_by=submitted_by,
        submitted_at=NOW,
        decided_by=decided_by,
        decided_at=NOW if decided_by else None,
        rejection_reason=None if status != "rejected" else "insufficient authority",
        fingerprint="",
    )
    from morva.runtime.evidence_submission import _fingerprint

    record.fingerprint = _fingerprint(
        evidence_id=record.evidence_id,
        source_type=record.source_type,
        source_uri=record.source_uri,
        source_sha256=record.source_sha256,
        issuer=record.issuer,
        population_scope=record.population_scope,
        submission_scope=Scope(record.submission_scope),
        submission_scope_id=record.submission_scope_id,
        effective_from=NOW,
        effective_to=record.effective_to,
        expires_at=record.expires_at,
        submitted_by=record.submitted_by,
        submitted_at=NOW,
    )
    return record


def test_accepted_submission_maps_to_m41_item():
    record = _record(evidence_id="E-002")
    item = submission_to_authoritative_item(record)

    assert item.evidence_id == "E-002"
    assert item.status == "accepted"
    assert item.approved_by == "approver"
    assert item.source_sha256 == "a" * 64


def test_non_accepted_submission_is_blocked():
    record = _record(evidence_id="E-PENDING", status="pending", decided_by=None)

    with pytest.raises(Exception):
        submission_to_authoritative_item(record)


def test_projection_excludes_pending_and_rejected():
    accepted = _record(evidence_id="E-ACCEPTED")
    pending = _record(evidence_id="E-PENDING", status="pending", decided_by=None)
    rejected = _record(evidence_id="E-REJECTED", status="rejected")

    registry, projection = build_registry_projection(
        (pending, rejected, accepted),
        projected_at=NOW,
    )

    assert [item.evidence_id for item in registry.items] == ["E-ACCEPTED"]
    assert projection.source_submission_count == 1
    assert projection.accepted_evidence_ids == ("E-ACCEPTED",)


def test_projection_is_deterministic_for_input_order():
    first = _record(evidence_id="E-001")
    second = _record(evidence_id="E-002")

    registry_one, projection_one = build_registry_projection(
        (first, second),
        projected_at=NOW,
    )
    registry_two, projection_two = build_registry_projection(
        (second, first),
        projected_at=NOW,
    )

    assert registry_one.fingerprint == registry_two.fingerprint
    assert projection_one.registry_fingerprint == projection_two.registry_fingerprint
    assert projection_one.projection_fingerprint == projection_two.projection_fingerprint


def test_projection_rejects_invalid_accepted_submission():
    record = _record(evidence_id="E-BAD", source_uri="not-a-uri")

    with pytest.raises(EvidenceRegistryBridgeError):
        build_registry_projection((record,), projected_at=NOW)


def test_projection_rejects_empty_registry():
    with pytest.raises(EvidenceRegistryBridgeError, match="empty"):
        build_registry_projection(
            (_record(evidence_id="E-PENDING", status="pending", decided_by=None),),
            projected_at=NOW,
        )


def test_projection_detects_duplicate_ids():
    first = _record(evidence_id="E-DUP")
    second = _record(evidence_id="E-DUP")

    with pytest.raises(EvidenceRegistryBridgeError, match="duplicate"):
        build_registry_projection((first, second), projected_at=NOW)


def test_projection_rejects_futureless_timezone_inputs():
    record = _record(evidence_id="E-TZ")
    record.effective_from = datetime(2026, 1, 1)
    with pytest.raises(EvidenceRegistryBridgeError, match="timezone"):
        submission_to_authoritative_item(record)
