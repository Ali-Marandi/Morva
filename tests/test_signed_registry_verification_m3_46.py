from datetime import datetime, timezone
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morva.runtime.release_evidence import EvidenceFile, ReleaseEvidenceBundle
from morva.runtime.release_manifest import ReleaseArtifact, ReleaseManifest
from morva.runtime.trusted_key_registry import TrustedKeyRegistry, TrustedSigningKey
from morva.runtime.signed_trusted_key_registry import SignedTrustedKeyRegistry
from tools.m3_44_evidence_verifier import verify_bundle


NOW = datetime(2026, 9, 18, 6, 0, tzinfo=timezone.utc)
SHA = "a" * 40
TAG = "v1.0.1"
RELEASE_ID = "morva-1.0.1"


def write_source_files(root: Path) -> tuple[Path, Path, Path, str, str, str]:
    from morva.runtime.release_attestation import ArtifactAttestation, ReleaseAttestation
    from morva.runtime.release_certification import ReleaseCertification
    from morva.runtime.release_gate import ReleaseGate
    from morva.runtime.release_rehearsal import ReleaseRehearsal
    from morva.runtime.security_assessment import SecurityAssessment

    manifest = ReleaseManifest(
        RELEASE_ID,
        TAG,
        SHA,
        (ReleaseArtifact("package.whl", "b" * 64, 4),),
    )
    manifest_file = root / "manifest.json"
    manifest_file.write_text(
        json.dumps(
            {
                "release_id": RELEASE_ID,
                "tag": TAG,
                "candidate_sha": SHA,
                "artifacts": [{"path": "package.whl", "sha256": "b" * 64, "size_bytes": 4}],
                "fingerprint": manifest.fingerprint,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    security = SecurityAssessment(
        assessment_id="SEC-M3-46",
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
    rehearsal = ReleaseRehearsal(SHA, TAG, manifest, gate)
    rehearsal_file = root / "rehearsal.json"
    rehearsal_file.write_text(
        json.dumps(
            {
                "release_id": RELEASE_ID,
                "tag": TAG,
                "candidate_sha": SHA,
                "manifest_fingerprint": manifest.fingerprint,
                "gate_fingerprint": gate.fingerprint,
                "rehearsal_fingerprint": rehearsal.fingerprint,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return (
        manifest_file,
        gate_file,
        rehearsal_file,
        manifest.fingerprint,
        gate.fingerprint,
        rehearsal.fingerprint,
    )


def write_signed_registry(root: Path, public_key) -> Path:
    registry = TrustedKeyRegistry(
        "morva-signing",
        1,
        (
            TrustedSigningKey(
                key_id=TrustedKeyRegistry.key_id_for(public_key),
                public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(public_key),
                status="active",
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        ),
    )
    root_key = Ed25519PrivateKey.generate()
    signed = SignedTrustedKeyRegistry(registry).sign(root_key, NOW)
    payload = {
        "registry": {
            "registry_id": registry.registry_id,
            "version": registry.version,
            "keys": [
                {
                    "key_id": item.key_id,
                    "public_key_sha256": item.public_key_sha256,
                    "status": item.status,
                    "valid_from": item.valid_from.isoformat(),
                    "valid_until": None,
                    "replacement_key_id": None,
                }
                for item in registry.keys
            ],
            "fingerprint": registry.fingerprint,
        },
        "signature": {
            "algorithm": signed.signature.algorithm,
            "root_key_id": signed.signature.root_key_id,
            "signature_b64": signed.signature.signature_b64,
            "signed_at": signed.signature.signed_at.isoformat(),
        },
        "fingerprint": signed.fingerprint,
    }
    registry_file = root / "registry.json"
    registry_file.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    public_file = root / "root-public.pem"
    public_file.write_bytes(
        root_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return registry_file, public_file


def make_bundle(root: Path):
    manifest, gate, rehearsal, mf, gf, rf = write_source_files(root)
    signer = Ed25519PrivateKey.generate()
    public = signer.public_key()
    files = tuple(
        EvidenceFile(name.name, __import__("hashlib").sha256(name.read_bytes()).hexdigest(), name.stat().st_size)
        for name in (manifest, gate, rehearsal)
    )
    signed = ReleaseEvidenceBundle(
        RELEASE_ID, TAG, SHA, mf, gf, rf, files
    ).sign(signer, NOW)
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
    public_file.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    registry_file, root_public_file = write_signed_registry(root, public)
    return bundle_file, public_file, registry_file, root_public_file, manifest, gate, rehearsal


def test_independent_verifier_reconstructs_signed_trust_chain(tmp_path: Path):
    bundle, public, registry, root_public, manifest, gate, rehearsal = make_bundle(tmp_path)
    verify_bundle(
        bundle,
        manifest,
        gate,
        rehearsal,
        public,
        registry,
        tmp_path,
        SHA,
        NOW,
        root_public,
    )


def test_independent_verifier_rejects_tampered_rehearsal(tmp_path: Path):
    bundle, public, registry, root_public, manifest, gate, rehearsal = make_bundle(tmp_path)
    payload = json.loads(rehearsal.read_text(encoding="utf-8"))
    payload["tag"] = "v9.9.9"
    rehearsal.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError):
        verify_bundle(
            bundle, public, registry, gate, tmp_path, SHA, NOW, root_public
        )


def test_independent_verifier_rejects_wrong_expected_sha(tmp_path: Path):
    bundle, public, registry, root_public, manifest, gate, rehearsal = make_bundle(tmp_path)

    with pytest.raises(ValueError, match="expected release commit"):
        verify_bundle(
            bundle,
            manifest,
            gate,
            rehearsal,
            public,
            registry,
            tmp_path,
            "f" * 40,
            NOW,
            root_public,
        )


def test_independent_verifier_rejects_unsigned_registry(tmp_path: Path):
    bundle, public, registry, root_public, manifest, gate, rehearsal = make_bundle(tmp_path)
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["signature"] = None
    registry.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="unsigned"):
        verify_bundle(
            bundle, public, manifest, gate, rehearsal, root_public, tmp_path, SHA, NOW, root_public
        )
