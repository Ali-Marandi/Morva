import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morva.runtime.release_evidence import EvidenceFile, ReleaseEvidenceBundle
from morva.runtime.release_manifest import ReleaseArtifact, ReleaseManifest
from morva.runtime.signed_trusted_key_registry import SignedTrustedKeyRegistry
from morva.runtime.trusted_key_registry import TrustedKeyRegistry, TrustedSigningKey
from tools.m3_44_evidence_verifier import verify_bundle


NOW = datetime(2026, 9, 18, 6, 0, tzinfo=timezone.utc)
SHA = "a" * 40
TAG = "v1.0.1"
RELEASE_ID = "morva-1.0.1"


def make_sources(root: Path):
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
                "artifacts": [
                    {"path": "package.whl", "sha256": "b" * 64, "size_bytes": 4}
                ],
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
    return manifest_file, gate_file, rehearsal_file, rehearsal


def write_bundle(root: Path, rehearsal):
    signer = Ed25519PrivateKey.generate()
    public = signer.public_key()
    root_key = Ed25519PrivateKey.generate()
    registry = TrustedKeyRegistry(
        "morva-signing",
        1,
        (
            TrustedSigningKey(
                key_id=TrustedKeyRegistry.key_id_for(public),
                public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(public),
                status="active",
                valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        ),
    )
    signed_registry = SignedTrustedKeyRegistry(registry).sign(root_key, NOW)
    registry_payload = {
        "registry": {
            "registry_id": registry.registry_id,
            "version": registry.version,
            "keys": [
                {
                    "key_id": item.key_id,
                    "public_key_sha256": item.public_key_sha256,
                    "status": item.status,
                    "valid_from": item.valid_from.isoformat(),
                    "valid_until": (
                        item.valid_until.isoformat() if item.valid_until else None
                    ),
                    "replacement_key_id": item.replacement_key_id,
                }
                for item in registry.keys
            ],
            "fingerprint": registry.fingerprint,
        },
        "signature": {
            "algorithm": signed_registry.signature.algorithm,
            "root_key_id": signed_registry.signature.root_key_id,
            "signature_b64": signed_registry.signature.signature_b64,
            "signed_at": signed_registry.signature.signed_at.isoformat(),
        },
        "fingerprint": signed_registry.fingerprint,
    }
    registry_file = root / "registry.json"
    registry_file.write_text(
        json.dumps(registry_payload, sort_keys=True),
        encoding="utf-8",
    )
    evidence_files = tuple(
        EvidenceFile(
            path.name,
            sha256(path.read_bytes()).hexdigest(),
            path.stat().st_size,
        )
        for path in (
            root / "manifest.json",
            root / "gate.json",
            root / "rehearsal.json",
            registry_file,
        )
    )
    bundle = ReleaseEvidenceBundle(
        RELEASE_ID,
        TAG,
        SHA,
        rehearsal.manifest.fingerprint,
        rehearsal.gate.fingerprint,
        rehearsal.fingerprint,
        registry.registry_id,
        registry.version,
        registry.fingerprint,
        evidence_files,
    ).sign(signer, NOW)
    bundle_payload = {
        "release_id": bundle.release_id,
        "tag": bundle.tag,
        "candidate_sha": bundle.candidate_sha,
        "manifest_fingerprint": bundle.manifest_fingerprint,
        "gate_fingerprint": bundle.gate_fingerprint,
        "rehearsal_fingerprint": bundle.rehearsal_fingerprint,
        "registry_id": bundle.registry_id,
        "registry_version": bundle.registry_version,
        "registry_fingerprint": bundle.registry_fingerprint,
        "evidence_files": [
            {
                "path": item.path,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
            }
            for item in bundle.evidence_files
        ],
        "fingerprint": bundle.fingerprint,
        "signature": {
            "algorithm": bundle.signature.algorithm,
            "key_id": bundle.signature.key_id,
            "signature_b64": bundle.signature.signature_b64,
            "signed_at": bundle.signature.signed_at.isoformat(),
        },
    }
    bundle_file = root / "bundle.json"
    bundle_file.write_text(
        json.dumps(bundle_payload, sort_keys=True),
        encoding="utf-8",
    )
    public_file = root / "public.pem"
    public_file.write_bytes(
        public.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    root_public_file = root / "root-public.pem"
    root_public_file.write_bytes(
        root_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    return bundle_file, public_file, registry_file, root_public_file



def test_independent_verifier_reconstructs_signed_trust_chain(tmp_path: Path):
    manifest, gate, rehearsal, rehearsal_obj = make_sources(tmp_path)
    bundle, public, registry, root_public = write_bundle(tmp_path, rehearsal_obj)

    verify_bundle(
        bundle_file=bundle,
        manifest_file=manifest,
        gate_file=gate,
        rehearsal_file=rehearsal,
        public_key_file=public,
        registry_file=registry,
        root=tmp_path,
        expected_sha=SHA,
        verified_at=NOW,
        registry_root_public_key=root_public,
    )


def test_independent_verifier_rejects_unsigned_registry(tmp_path: Path):
    manifest, gate, rehearsal, rehearsal_obj = make_sources(tmp_path)
    bundle, public, registry, root_public = write_bundle(tmp_path, rehearsal_obj)
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["signature"] = None
    registry.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="unsigned"):
        verify_bundle(
            bundle_file=bundle,
            manifest_file=manifest,
            gate_file=gate,
            rehearsal_file=rehearsal,
            public_key_file=public,
            registry_file=registry,
            root=tmp_path,
            expected_sha=SHA,
            verified_at=NOW,
            registry_root_public_key=root_public,
        )


def test_independent_verifier_rejects_wrong_expected_sha(tmp_path: Path):
    manifest, gate, rehearsal, rehearsal_obj = make_sources(tmp_path)
    bundle, public, registry, root_public = write_bundle(tmp_path, rehearsal_obj)

    with pytest.raises(ValueError, match="expected release commit"):
        verify_bundle(
            bundle_file=bundle,
            manifest_file=manifest,
            gate_file=gate,
            rehearsal_file=rehearsal,
            public_key_file=public,
            registry_file=registry,
            root=tmp_path,
            expected_sha="f" * 40,
            verified_at=NOW,
            registry_root_public_key=root_public,
        )
