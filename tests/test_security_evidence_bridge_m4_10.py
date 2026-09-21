from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.security_assessment import SecurityAssessment
from morva.runtime.security_evidence_bridge import (
    SecurityEvidenceBridgeError,
    build_security_evidence_binding,
)

NOW = datetime(2026, 9, 22, 12, 0, tzinfo=timezone.utc)
SCOPE_HASH = sha256(b"m4-10-security-scope").hexdigest()


def _assessment(**overrides):
    controls = ("authentication", "authorization", "cryptography")
    values = {
        "assessment_id": "SEC-EXT-001",
        "assessed_at": NOW,
        "scope_hash": SCOPE_HASH,
        "required_controls": controls,
        "verified_controls": controls,
        "independent_assessor": "independent-security-firm",
        "independent_report_uri": "https://authority.example/security/report-001",
        "independent_signed_at": NOW,
    }
    values.update(overrides)
    return SecurityAssessment(**values)


def _authority(assessment=None, **overrides):
    item = assessment or _assessment()
    payload = {
        "intake_version": 1,
        "evidence_id": "SEC-EVID-001",
        "source_type": "security_assessment",
        "source_uri": item.independent_report_uri,
        "source_sha256": item.fingerprint,
        "issuer": "security-authority",
        "population_scope": "enterprise",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "security-approver",
        "approved_at": "2026-09-21T10:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def test_release_ready_security_assessment_binds():
    assessment = _assessment()
    binding = build_security_evidence_binding(
        assessment,
        build_registry((_authority(assessment),), registered_at=NOW),
        authoritative_evidence_id="SEC-EVID-001",
        bound_by="security-binder",
        bound_at=NOW,
    )
    assert binding.assessment_id == "SEC-EXT-001"
    assert binding.assessor == "independent-security-firm"
    assert len(binding.fingerprint) == 64


def test_not_release_ready_is_rejected():
    assessment = _assessment(independent_assessor=None)
    with pytest.raises(SecurityEvidenceBridgeError, match="release-ready"):
        build_security_evidence_binding(
            assessment,
            build_registry((_authority(assessment, source_sha256=assessment.fingerprint),), registered_at=NOW),
            authoritative_evidence_id="SEC-EVID-001",
            bound_by="security-binder",
            bound_at=NOW,
        )


def test_report_uri_mismatch_is_rejected():
    assessment = _assessment()
    authority = _authority(assessment)
    authority_payload = authority.to_payload()
    authority_payload.pop("fingerprint", None)
    authority_payload["source_uri"] = "https://other.example/report"
    authority = AuthoritativeEvidenceItem(**authority_payload)
    with pytest.raises(SecurityEvidenceBridgeError, match="URI"):
        build_security_evidence_binding(
            assessment,
            build_registry((authority,), registered_at=NOW),
            authoritative_evidence_id="SEC-EVID-001",
            bound_by="security-binder",
            bound_at=NOW,
        )


def test_digest_mismatch_is_rejected():
    assessment = _assessment()
    authority = _authority(assessment, source_sha256="b" * 64)
    with pytest.raises(SecurityEvidenceBridgeError, match="fingerprint"):
        build_security_evidence_binding(
            assessment,
            build_registry((authority,), registered_at=NOW),
            authoritative_evidence_id="SEC-EVID-001",
            bound_by="security-binder",
            bound_at=NOW,
        )


def test_expired_authority_is_rejected():
    assessment = _assessment()
    authority = _authority(
        assessment,
        expires_at="2026-09-21T23:59:59+00:00",
    )
    with pytest.raises(SecurityEvidenceBridgeError, match="expired"):
        build_security_evidence_binding(
            assessment,
            build_registry((authority,), registered_at=NOW),
            authoritative_evidence_id="SEC-EVID-001",
            bound_by="security-binder",
            bound_at=NOW,
        )


def test_future_signed_report_is_rejected():
    assessment = _assessment(
        independent_signed_at=datetime(2026, 9, 23, 10, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(SecurityEvidenceBridgeError, match="future-dated"):
        build_security_evidence_binding(
            assessment,
            build_registry((_authority(assessment),), registered_at=NOW),
            authoritative_evidence_id="SEC-EVID-001",
            bound_by="security-binder",
            bound_at=NOW,
        )


def test_binding_actor_must_differ_from_assessor():
    assessment = _assessment()
    with pytest.raises(SecurityEvidenceBridgeError, match="differ"):
        build_security_evidence_binding(
            assessment,
            build_registry((_authority(assessment),), registered_at=NOW),
            authoritative_evidence_id="SEC-EVID-001",
            bound_by=assessment.independent_assessor,
            bound_at=NOW,
        )


def test_open_high_finding_is_blocking():
    from morva.runtime.security_assessment import SecurityFinding

    assessment = _assessment(
        findings=(SecurityFinding("SEC-001", "high", "open"),),
    )
    with pytest.raises(SecurityEvidenceBridgeError, match="release-ready"):
        build_security_evidence_binding(
            assessment,
            build_registry((_authority(assessment),), registered_at=NOW),
            authoritative_evidence_id="SEC-EVID-001",
            bound_by="security-binder",
            bound_at=NOW,
        )
