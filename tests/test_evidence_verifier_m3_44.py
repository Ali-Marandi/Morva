import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morva.runtime.release_evidence import EvidenceFile, ReleaseEvidenceBundle
from morva.runtime.trusted_key_registry import TrustedKeyRegistry, TrustedSigningKey
from tools.m3_44_evidence_verifier import verify_bundle


NOW = datetime(2026, 9, 18, 4, 0, tzinfo=timezone.utc)
SHA = "a" * 40
TAG = "v1.0.1"
RELEASE_ID = "morva-1.0.1"


def write_source_files(root: Path) -> tuple[Path, Path, Path, str, str, str]:
    manifest_payload = {
        "release_id": RELEASE_ID,
        "tag": TAG,
        "candidate_sha": SHA,
        "artifacts": [{"path": "package.whl", "sha256": "b" * 64, "size_bytes": 4}],
    }
    from morva.runtime.release_manifest import ReleaseManifest, ReleaseArtifact

    manifest = ReleaseManifest(
        RELEASE_ID, TAG, SHA, (ReleaseArtifact("package.whl", "b" * 64, 4),)
    )
    manifest_payload["fingerprint"] = manifest.fingerprint
    manifest_file = root / "manifest.json"
    manifest_file.write_text(
        json.dumps(manifest_payload, sort_keys=True), encoding="utf-8"
    )

    from morva.runtime.release_certification import ReleaseCertification
    from morva.runtime.release_gate import ReleaseGate
    from morva.runtime.release_attestation import ArtifactAttestation, ReleaseAttestation
    from morva.runtime.security_assessment import SecurityAssessment

    security = SecurityAssessment(
        assessment_id="SEC-M3-44",
        assessed_at=NOW,
        scope_hash="c" * 64,
        required_controls=("authentication",),
        verified_controls=(),
    )
    certification = ReleaseCertification(
        RELEASE_ID, SHA, ("security-report",), ()
    )
    attestation = ReleaseAttestation(
        RELEASE_ID,
        TAG,
        SHA,
        certification.fingerprint,
        "d" * 64,
        (ArtifactAttestation("package.whl", "b" * 64),),
    )
    gate = ReleaseGate(SHA, security, certification, attestation)
    gate_file = root / "gate.json"
    gate_file.write_text(
        json.dumps(
            {
                "candidate_sha": SHA,
                "security_assessment": {
                    "assessment_id": security.assessment_id,
                    "assessed_at": NOW.isoformat(),
                    "scope_hash": security.scope_hash,
                    "required_controls": list(security.required_controls),
                    "verified_controls": list(security.verified_controls),
                    "findings": [],
                    "independent_assessor": None,
                    "independent_report_uri": None,
                    "independent_signed_at": None,
                },
                "certification": {
                    "release_id": certification.release_id,
                    "candidate_sha": certification.candidate_sha,
                    "required_evidence": list(certification.required_evidence),
                    "verified_evidence": list(certification.verified_evidence),
                    "security_signoff_complete": False,
                    "disaster_recovery_signoff_complete": False,
                    "load_signoff_complete": False,
                    "reconciliation_signoff_complete": False,
                    "signoffs": [],
                },
                "attestation": {
                    "release_id": attestation.release_id,
                    "tag": attestation.tag,
                    "candidate_sha": attestation.candidate_sha,
                    "certification_fingerprint": attestation.certification_fingerprint,
                    "evidence_bundle_fingerprint": attestation.evidence_bundle_fingerprint,
                    "artifacts": [
                        {"path": item.path, "sha256": item.sha256}
                        for item in attestation.artifacts
                    ],
                    "signer": None,
                    "signed_at": None,
                    "signature_uri": None,
                    "release_uri": None,
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    rehearsal = {
        "release_id": RELEASE_ID,
        "tag": TAG,
        "candidate_sha": SHA,
        "manifest_fingerprint": manifest.fingerprint,
        "gate_fingerprint": gate.fingerprint,
    }
    from morva.runtime.release_rehearsal import ReleaseRehearsal

    rehearsal_obj = ReleaseRehearsal(SHA, TAG, manifest, gate)
    rehearsal["rehearsal_fingerprint"] = rehearsal_obj.fingerprint
    rehearsal_file = root / "rehearsal.json"
    rehearsal_file.write_text(json.dumps(rehearsal, sort_keys=True), encoding="utf-8")
    return (
        manifest_file,
        gate_file,
        rehearsal_file,
        manifest.fingerprint,
        gate.fingerprint,
        rehearsal_obj.fingerprint,
    )


def make_bundle(root: Path) -> tuple[Path, Path, Path]:
    manifest, gate, rehearsal, mf, gf, rf = write_source_files(root)
    paths = (manifest, gate, rehearsal)
    evidence = tuple(
        EvidenceFile(
            path.name,
            sha256(path.read_bytes()).hexdigest(),
            path.stat().st_size,
        )
        for path in paths
    )
    bundle = ReleaseEvidenceBundle(
        RELEASE_ID, TAG, SHA, mf, gf, rf, evidence
    )
    private_key = Ed25519PrivateKey.generate()
    signed = bundle.sign(private_key, NOW)

    bundle_payload = {
        "release_id": signed.release_id,
        "tag": signed.tag,
        "candidate_sha": signed.candidate_sha,
        "manifest_fingerprint": signed.manifest_fingerprint,
        "gate_fingerprint": signed.gate_fingerprint,
        "rehearsal_fingerprint": signed.rehearsal_fingerprint,
        "evidence_files": [
            {"path": item.path, "sha256": item.sha256, "size_bytes": item.size_bytes}
            for item in signed.evidence_files
        ],
        "fingerprint": signed.fingerprint,
        "signature": {
            "algorithm": signed.signature.algorithm,
            "key_id": signed.signature.key_id,
            "signature_b64": signed.signature.signature_b64,
            "signed_at": signed.signature.signed_at.isoformat(),
        },
    }
    bundle_file = root / "bundle.json"
    bundle_file.write_text(json.dumps(bundle_payload, sort_keys=True), encoding="utf-8")
    public_file = root / "public.pem"
    public_key = private_key.public_key()
    public_file.write_bytes(
        public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    registry = TrustedKeyRegistry(
        registry_id="morva-ci",
        version=1,
        keys=(
            TrustedSigningKey(
                key_id=TrustedKeyRegistry.key_id_for(public_key),
                public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(public_key),
                status="active",
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        ),
    )
    registry_file = root / "registry.json"
    registry_file.write_text(
        json.dumps(
            {
                "registry_id": registry.registry_id,
                "version": registry.version,
                "keys": [
                    {
                        "key_id": item.key_id,
                        "public_key_sha256": item.public_key_sha256,
                        "status": item.status,
                        "valid_from": item.valid_from.isoformat(),
                        "valid_until": item.valid_until.isoformat()
                        if item.valid_until
                        else None,
                        "replacement_key_id": item.replacement_key_id,
                    }
                    for item in registry.keys
                ],
                "fingerprint": registry.fingerprint,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return bundle_file, public_file, registry_file


def test_independent_verifier_reconstructs_and_verifies_chain(tmp_path: Path):
    bundle_file, public_file, registry_file = make_bundle(tmp_path)
    verify_bundle(
        bundle_file,
        tmp_path / "manifest.json",
        tmp_path / "gate.json",
        tmp_path / "rehearsal.json",
        public_file,
        registry_file,
        tmp_path,
        SHA,
    )


def test_independent_verifier_rejects_tampered_rehearsal(tmp_path: Path):
    bundle_file, public_file = make_bundle(tmp_path)
    path = tmp_path / "rehearsal.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["tag"] = "v9.9.9"
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    import pytest

    with pytest.raises(ValueError):
        verify_bundle(
            bundle_file,
            tmp_path / "manifest.json",
            tmp_path / "gate.json",
            path,
            public_file,
            tmp_path,
            SHA,
        )


def test_independent_verifier_rejects_wrong_expected_sha(tmp_path: Path):
    bundle_file, public_file = make_bundle(tmp_path)

    import pytest

    with pytest.raises(ValueError, match="expected release commit"):
        verify_bundle(
            bundle_file,
            tmp_path / "manifest.json",
            tmp_path / "gate.json",
            tmp_path / "rehearsal.json",
            public_file,
            tmp_path,
            "f" * 40,
        )
