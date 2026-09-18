from datetime import datetime, timezone
from pathlib import Path

import pytest

from morva.runtime.release_attestation import ArtifactAttestation, ReleaseAttestation
from morva.runtime.release_certification import CertificationSignoff, ReleaseCertification
from morva.runtime.release_gate import ReleaseGate
from morva.runtime.release_manifest import ReleaseManifest
from morva.runtime.release_rehearsal import ReleaseRehearsal, ReleaseRehearsalError
from morva.runtime.security_assessment import SecurityAssessment

NOW = datetime(2026, 9, 18, 2, 0, tzinfo=timezone.utc)
SHA = "a" * 40
TAG = "v1.0.1"
RELEASE_ID = "morva-1.0.1"
CONTROLS = ("authentication", "authorization", "cryptography", "auditability")
EVIDENCE = ("security-report", "dr-evidence", "load-evidence", "reconciliation-evidence")


def make_manifest(tmp_path: Path) -> ReleaseManifest:
    (tmp_path / "morva-1.0.1-py3-none-any.whl").write_bytes(b"wheel")
    (tmp_path / "morva-1.0.1.tar.gz").write_bytes(b"source")
    from tools.m3_41_release_manifest import build_manifest

    return build_manifest(tmp_path, RELEASE_ID, TAG, SHA)


def make_gate(manifest: ReleaseManifest, ready: bool = True) -> ReleaseGate:
    security = SecurityAssessment(
        assessment_id="SEC-M3-42",
        assessed_at=NOW,
        scope_hash="b" * 64,
        required_controls=CONTROLS,
        verified_controls=CONTROLS if ready else CONTROLS[:-1],
        independent_assessor="independent-assessor" if ready else None,
        independent_report_uri="evidence://security" if ready else None,
        independent_signed_at=NOW if ready else None,
    )
    cert = ReleaseCertification(
        release_id=RELEASE_ID,
        candidate_sha=SHA,
        required_evidence=EVIDENCE,
        verified_evidence=EVIDENCE if ready else EVIDENCE[:-1],
        security_signoff_complete=ready,
        disaster_recovery_signoff_complete=ready,
        load_signoff_complete=ready,
        reconciliation_signoff_complete=ready,
        signoffs=(
            CertificationSignoff("finance", "finance", NOW, "evidence://finance"),
            CertificationSignoff("legal", "legal", NOW, "evidence://legal"),
            CertificationSignoff("operations", "operations", NOW, "evidence://operations"),
        )
        if ready
        else (),
    )
    artifacts = tuple(
        ArtifactAttestation(item.path, item.sha256) for item in manifest.artifacts
    )
    attestation = ReleaseAttestation(
        release_id=RELEASE_ID,
        tag=TAG,
        candidate_sha=SHA,
        certification_fingerprint=cert.fingerprint,
        evidence_bundle_fingerprint="d" * 64,
        artifacts=artifacts,
        signer="release-signer" if ready else None,
        signed_at=NOW if ready else None,
        signature_uri="evidence://signature" if ready else None,
        release_uri="evidence://release" if ready else None,
    )
    return ReleaseGate(SHA, security, cert, attestation)


def test_release_rehearsal_passes_with_exact_manifest_gate_binding(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    rehearsal = ReleaseRehearsal(SHA, TAG, manifest, make_gate(manifest))

    rehearsal.assert_consistent(tmp_path)
    rehearsal.assert_release_ready(tmp_path)
    assert rehearsal.release_ready is True
    assert len(rehearsal.fingerprint) == 64


def test_release_rehearsal_rejects_candidate_sha_mismatch(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    with pytest.raises(ReleaseRehearsalError, match="manifest candidate_sha"):
        ReleaseRehearsal("f" * 40, TAG, manifest, make_gate(manifest))


def test_release_rehearsal_rejects_attestation_tag_mismatch(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    gate = make_gate(manifest)
    attestation = ReleaseAttestation(
        release_id=gate.attestation.release_id,
        tag="v9.9.9",
        candidate_sha=gate.attestation.candidate_sha,
        certification_fingerprint=gate.attestation.certification_fingerprint,
        evidence_bundle_fingerprint=gate.attestation.evidence_bundle_fingerprint,
        artifacts=gate.attestation.artifacts,
        signer=gate.attestation.signer,
        signed_at=gate.attestation.signed_at,
        signature_uri=gate.attestation.signature_uri,
        release_uri=gate.attestation.release_uri,
    )
    tampered_gate = ReleaseGate(SHA, gate.security_assessment, gate.certification, attestation)

    with pytest.raises(ReleaseRehearsalError, match="attestation tag"):
        ReleaseRehearsal(SHA, TAG, manifest, tampered_gate)


def test_release_rehearsal_rejects_artifact_hash_mismatch(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    gate = make_gate(manifest)
    tampered_artifacts = (
        ArtifactAttestation(manifest.artifacts[0].path, "f" * 64),
        *gate.attestation.artifacts[1:],
    )
    tampered_attestation = ReleaseAttestation(
        release_id=gate.attestation.release_id,
        tag=gate.attestation.tag,
        candidate_sha=gate.attestation.candidate_sha,
        certification_fingerprint=gate.attestation.certification_fingerprint,
        evidence_bundle_fingerprint=gate.attestation.evidence_bundle_fingerprint,
        artifacts=tampered_artifacts,
        signer=gate.attestation.signer,
        signed_at=gate.attestation.signed_at,
        signature_uri=gate.attestation.signature_uri,
        release_uri=gate.attestation.release_uri,
    )
    tampered_gate = ReleaseGate(
        SHA, gate.security_assessment, gate.certification, tampered_attestation
    )

    with pytest.raises(ReleaseRehearsalError, match="exactly match"):
        ReleaseRehearsal(SHA, TAG, manifest, tampered_gate)


def test_release_rehearsal_detects_artifact_tampering(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    rehearsal = ReleaseRehearsal(SHA, TAG, manifest, make_gate(manifest))
    (tmp_path / manifest.artifacts[0].path).write_bytes(b"tampered")

    with pytest.raises(ReleaseRehearsalError, match="sha256 mismatch"):
        rehearsal.assert_consistent(tmp_path)


def test_release_rehearsal_can_rehearse_blocked_gate_without_fake_approval(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    rehearsal = ReleaseRehearsal(SHA, TAG, manifest, make_gate(manifest, ready=False))

    rehearsal.assert_consistent(tmp_path)
    assert rehearsal.release_ready is False
    assert rehearsal.blockers
    with pytest.raises(ReleaseRehearsalError, match="incomplete"):
        rehearsal.assert_release_ready(tmp_path)


def test_rehearsal_fingerprint_is_deterministic(tmp_path: Path):
    manifest = make_manifest(tmp_path)
    first = ReleaseRehearsal(SHA, TAG, manifest, make_gate(manifest))
    second = ReleaseRehearsal(SHA, TAG, manifest, make_gate(manifest))

    assert first.fingerprint == second.fingerprint
