from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morva.runtime.release_attestation import ArtifactAttestation, ReleaseAttestation
from morva.runtime.release_certification import CertificationSignoff, ReleaseCertification
from morva.runtime.release_evidence import (
    EvidenceBundleSignature,
    EvidenceFile,
    ReleaseEvidenceBundle,
    ReleaseEvidenceError,
)
from morva.runtime.release_gate import ReleaseGate
from morva.runtime.release_manifest import ReleaseArtifact, ReleaseManifest
from morva.runtime.release_rehearsal import ReleaseRehearsal
from morva.runtime.security_assessment import SecurityAssessment

NOW = datetime(2026, 9, 18, 3, 0, tzinfo=timezone.utc)
SHA = "a" * 40
TAG = "v1.0.1"
RELEASE_ID = "morva-1.0.1"
REGISTRY_ID = "morva-signing"
REGISTRY_VERSION = 1
REGISTRY_FINGERPRINT = "e" * 64


def make_rehearsal(tmp_path: Path) -> ReleaseRehearsal:
    for name, content in (
        ("manifest.json", "manifest"),
        ("gate.json", "gate"),
        ("rehearsal.json", "rehearsal"),
    ):
        (tmp_path / name).write_text(content, encoding="utf-8")
    manifest = ReleaseManifest(
        release_id=RELEASE_ID,
        tag=TAG,
        candidate_sha=SHA,
        artifacts=(ReleaseArtifact("package.whl", "b" * 64, 10),),
    )
    security = SecurityAssessment(
        assessment_id="SEC-M3-43",
        assessed_at=NOW,
        scope_hash="c" * 64,
        required_controls=("authentication",),
        verified_controls=("authentication",),
        independent_assessor="assessor",
        independent_report_uri="evidence://security",
        independent_signed_at=NOW,
    )
    cert = ReleaseCertification(
        release_id=RELEASE_ID,
        candidate_sha=SHA,
        required_evidence=("security-report",),
        verified_evidence=("security-report",),
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
    attestation = ReleaseAttestation(
        release_id=RELEASE_ID,
        tag=TAG,
        candidate_sha=SHA,
        certification_fingerprint=cert.fingerprint,
        evidence_bundle_fingerprint="d" * 64,
        artifacts=(ArtifactAttestation("package.whl", "b" * 64),),
        signer="signer",
        signed_at=NOW,
        signature_uri="evidence://signature",
        release_uri="evidence://release",
    )
    return ReleaseRehearsal(SHA, TAG, manifest, ReleaseGate(SHA, security, cert, attestation))


def make_bundle(tmp_path: Path) -> tuple[ReleaseEvidenceBundle, Ed25519PrivateKey]:
    rehearsal = make_rehearsal(tmp_path)
    files = tuple(
        EvidenceFile(
            name,
            sha256((tmp_path / name).read_bytes()).hexdigest(),
            (tmp_path / name).stat().st_size,
        )
        for name in ("manifest.json", "gate.json", "rehearsal.json")
    )
    bundle = ReleaseEvidenceBundle(
        release_id=RELEASE_ID,
        tag=TAG,
        candidate_sha=SHA,
        manifest_fingerprint=rehearsal.manifest.fingerprint,
        gate_fingerprint=rehearsal.gate.fingerprint,
        rehearsal_fingerprint=rehearsal.fingerprint,
        registry_id=REGISTRY_ID,
        registry_version=REGISTRY_VERSION,
        registry_fingerprint=REGISTRY_FINGERPRINT,
        evidence_files=files,
    )
    return bundle, Ed25519PrivateKey.generate()


def test_signed_bundle_round_trips_and_verifies_files(tmp_path: Path):
    bundle, private_key = make_bundle(tmp_path)
    signed = bundle.sign(private_key, NOW)

    signed.verify_files(tmp_path)
    signed.verify_signature(private_key.public_key())
    signed.assert_matches_rehearsal(make_rehearsal(tmp_path))
    signed.assert_signed()
    assert signed.signature is not None


def test_signature_timestamp_is_bound_to_the_signed_payload(tmp_path: Path):
    bundle, private_key = make_bundle(tmp_path)
    signed = bundle.sign(private_key, NOW)
    changed_context = EvidenceBundleSignature(
        algorithm=signed.signature.algorithm,
        key_id=signed.signature.key_id,
        signature_b64=signed.signature.signature_b64,
        signed_at=datetime(2026, 9, 19, 3, 0, tzinfo=timezone.utc),
    )
    changed = ReleaseEvidenceBundle(
        release_id=signed.release_id,
        tag=signed.tag,
        candidate_sha=signed.candidate_sha,
        manifest_fingerprint=signed.manifest_fingerprint,
        gate_fingerprint=signed.gate_fingerprint,
        rehearsal_fingerprint=signed.rehearsal_fingerprint,
        registry_id=signed.registry_id,
        registry_version=signed.registry_version,
        registry_fingerprint=signed.registry_fingerprint,
        evidence_files=signed.evidence_files,
        signature=changed_context,
    )
    with pytest.raises(ReleaseEvidenceError, match="verification failed"):
        changed.verify_signature(private_key.public_key())


def test_bundle_rejects_wrong_public_key(tmp_path: Path):
    bundle, private_key = make_bundle(tmp_path)
    signed = bundle.sign(private_key, NOW)

    with pytest.raises(ReleaseEvidenceError, match="key_id"):
        signed.verify_signature(Ed25519PrivateKey.generate().public_key())


def test_bundle_detects_evidence_file_tampering(tmp_path: Path):
    bundle, private_key = make_bundle(tmp_path)
    signed = bundle.sign(private_key, NOW)
    (tmp_path / "gate.json").write_text("tampered", encoding="utf-8")

    with pytest.raises(ReleaseEvidenceError, match="sha256 mismatch"):
        signed.verify_files(tmp_path)


def test_bundle_rejects_unsigned_and_bad_signature_shape():
    bundle = ReleaseEvidenceBundle(
        release_id=RELEASE_ID,
        tag=TAG,
        candidate_sha=SHA,
        manifest_fingerprint="a" * 64,
        gate_fingerprint="b" * 64,
        rehearsal_fingerprint="c" * 64,
        registry_id=REGISTRY_ID,
        registry_version=REGISTRY_VERSION,
        registry_fingerprint=REGISTRY_FINGERPRINT,
        evidence_files=(EvidenceFile("manifest.json", "d" * 64, 1),),
    )

    with pytest.raises(ReleaseEvidenceError, match="unsigned"):
        bundle.assert_signed()

    with pytest.raises(ReleaseEvidenceError, match="64 bytes"):
        EvidenceBundleSignature(
            algorithm="Ed25519",
            key_id="key",
            signature_b64="eA==",
            signed_at=NOW,
        )


def test_bundle_fingerprint_changes_when_bound_identity_changes():
    base = ReleaseEvidenceBundle(
        release_id=RELEASE_ID,
        tag=TAG,
        candidate_sha=SHA,
        manifest_fingerprint="a" * 64,
        gate_fingerprint="b" * 64,
        rehearsal_fingerprint="c" * 64,
        registry_id=REGISTRY_ID,
        registry_version=REGISTRY_VERSION,
        registry_fingerprint=REGISTRY_FINGERPRINT,
        evidence_files=(EvidenceFile("manifest.json", "d" * 64, 1),),
    )
    changed = ReleaseEvidenceBundle(
        release_id=RELEASE_ID,
        tag="v9.9.9",
        candidate_sha=SHA,
        manifest_fingerprint="a" * 64,
        gate_fingerprint="b" * 64,
        rehearsal_fingerprint="c" * 64,
        registry_id=REGISTRY_ID,
        registry_version=REGISTRY_VERSION,
        registry_fingerprint=REGISTRY_FINGERPRINT,
        evidence_files=(EvidenceFile("manifest.json", "d" * 64, 1),),
    )
    assert base.fingerprint != changed.fingerprint


def test_registry_binding_changes_bundle_fingerprint():
    first = ReleaseEvidenceBundle(
        release_id=RELEASE_ID,
        tag=TAG,
        candidate_sha=SHA,
        manifest_fingerprint="a" * 64,
        gate_fingerprint="b" * 64,
        rehearsal_fingerprint="c" * 64,
        registry_id=REGISTRY_ID,
        registry_version=REGISTRY_VERSION,
        registry_fingerprint=REGISTRY_FINGERPRINT,
        evidence_files=(EvidenceFile("manifest.json", "d" * 64, 1),),
    )
    changed = ReleaseEvidenceBundle(
        release_id=RELEASE_ID,
        tag=TAG,
        candidate_sha=SHA,
        manifest_fingerprint="a" * 64,
        gate_fingerprint="b" * 64,
        rehearsal_fingerprint="c" * 64,
        registry_id=REGISTRY_ID,
        registry_version=REGISTRY_VERSION + 1,
        registry_fingerprint=REGISTRY_FINGERPRINT,
        evidence_files=(EvidenceFile("manifest.json", "d" * 64, 1),),
    )

    assert first.fingerprint != changed.fingerprint



def test_registry_metadata_is_included_in_signature_payload(tmp_path: Path):
    private_key = Ed25519PrivateKey.generate()
    bundle, _ = make_bundle(tmp_path)
    signed = bundle.sign(private_key, NOW)
    payload = signed.signing_bytes(signed.signature).decode("utf-8")

    assert '"registry_id":"morva-signing"' in payload
    assert '"registry_version":1' in payload
    assert '"registry_fingerprint":"' + REGISTRY_FINGERPRINT + '"' in payload
