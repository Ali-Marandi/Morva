from datetime import datetime, timezone

import pytest

from morva.runtime.release_attestation import ArtifactAttestation, ReleaseAttestation
from morva.runtime.release_certification import CertificationSignoff, ReleaseCertification
from morva.runtime.release_gate import ReleaseGate, ReleaseGateError
from morva.runtime.security_assessment import SecurityAssessment


NOW = datetime(2026, 9, 17, 19, 0, tzinfo=timezone.utc)
SHA = "a" * 40
CONTROL = ("authentication", "authorization", "cryptography", "auditability")
EVIDENCE = ("security-report", "dr-evidence", "load-evidence", "reconciliation-evidence")


def security(ready: bool = True) -> SecurityAssessment:
    return SecurityAssessment(
        assessment_id="SEC-M3-40",
        assessed_at=NOW,
        scope_hash="b" * 64,
        required_controls=CONTROL,
        verified_controls=CONTROL if ready else CONTROL[:-1],
        independent_assessor="independent-assessor" if ready else None,
        independent_report_uri="evidence://security" if ready else None,
        independent_signed_at=NOW if ready else None,
    )


def certification(ready: bool = True) -> ReleaseCertification:
    signoffs = (
        CertificationSignoff("finance", "finance", NOW, "evidence://finance"),
        CertificationSignoff("legal", "legal", NOW, "evidence://legal"),
        CertificationSignoff("operations", "operations", NOW, "evidence://operations"),
    ) if ready else ()
    return ReleaseCertification(
        release_id="morva-1.0.1",
        candidate_sha=SHA,
        required_evidence=EVIDENCE,
        verified_evidence=EVIDENCE if ready else EVIDENCE[:-1],
        security_signoff_complete=ready,
        disaster_recovery_signoff_complete=ready,
        load_signoff_complete=ready,
        reconciliation_signoff_complete=ready,
        signoffs=signoffs,
    )


def attestation(ready: bool = True) -> ReleaseAttestation:
    return ReleaseAttestation(
        release_id="morva-1.0.1",
        tag="v1.0.1",
        candidate_sha=SHA,
        certification_fingerprint="c" * 64,
        evidence_bundle_fingerprint="d" * 64,
        artifacts=(ArtifactAttestation("dist/morva.tar.gz", "e" * 64),) if ready else (),
        signer="release-signer" if ready else None,
        signed_at=NOW if ready else None,
        signature_uri="evidence://signature" if ready else None,
        release_uri="https://github.com/Ali-Marandi/Morva/releases/tag/v1.0.1" if ready else None,
    )


def test_aggregate_release_gate_requires_every_domain():
    gate = ReleaseGate(SHA, security(), certification(False), attestation())

    assert gate.release_ready is False
    assert "formal release certification is incomplete" in gate.blockers
    with pytest.raises(ReleaseGateError, match="formal release certification"):
        gate.assert_release_ready()


def test_aggregate_release_gate_passes_only_when_all_contracts_are_ready():
    gate = ReleaseGate(SHA, security(), certification(), attestation())

    assert gate.release_ready is True
    gate.assert_release_ready()
    assert len(gate.fingerprint) == 64
    assert gate.fingerprint == gate.fingerprint


def test_aggregate_release_gate_rejects_sha_mismatch():
    mismatched = ReleaseCertification(
        release_id="morva-1.0.1",
        candidate_sha="f" * 40,
        required_evidence=EVIDENCE,
        verified_evidence=EVIDENCE,
        security_signoff_complete=True,
        disaster_recovery_signoff_complete=True,
        load_signoff_complete=True,
        reconciliation_signoff_complete=True,
        signoffs=(
            CertificationSignoff("finance", "finance", NOW, "evidence://finance"),
            CertificationSignoff("legal", "legal", NOW, "evidence://legal"),
            CertificationSignoff("operations", "operations", NOW, "evidence://operations"),
        ),
    )

    with pytest.raises(ReleaseGateError, match="candidate_sha"):
        ReleaseGate(SHA, security(), mismatched, attestation())


def test_gate_blockers_surface_security_and_attestation_failures():
    gate = ReleaseGate(SHA, security(False), certification(), attestation(False))

    assert any("independent security signoff" in item for item in gate.blockers)
    assert any("release provenance/signing attestation" in item for item in gate.blockers)
