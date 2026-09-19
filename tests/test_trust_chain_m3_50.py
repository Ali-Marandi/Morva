from datetime import datetime, timedelta, timezone
import json
from hashlib import sha256
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from morva.runtime.release_evidence import EvidenceFile, ReleaseEvidenceBundle
from morva.runtime.release_manifest import ReleaseArtifact, ReleaseManifest
from morva.runtime.release_rehearsal import ReleaseRehearsal
from morva.runtime.release_gate import ReleaseGate
from morva.runtime.release_attestation import ArtifactAttestation, ReleaseAttestation
from morva.runtime.release_certification import ReleaseCertification
from morva.runtime.security_assessment import SecurityAssessment
from morva.runtime.root_trust_rotation import RootRotationCeremony
from morva.runtime.trust_chain import TrustChainVerificationError, verify_trust_chain
from morva.runtime.trust_rotation import TrustRegistryRotationCeremony
from morva.runtime.signed_trusted_key_registry import SignedTrustedKeyRegistry
from morva.runtime.trusted_key_registry import TrustedKeyRegistry, TrustedSigningKey
from tools.m3_46_signed_trusted_registry import write_signed_registry
from tools.m3_49_root_trust_rotation import write_ceremony as write_root_ceremony
from tools.m3_48_trust_rotation import write_ceremony as write_signing_ceremony
from tools.m3_50_trust_chain_verifier import verify_chain


NOW = datetime(2026, 9, 19, 10, 0, tzinfo=timezone.utc)
SIGN_EFFECTIVE = NOW + timedelta(hours=1)
ROOT_EFFECTIVE = NOW + timedelta(hours=2)
VERIFY_AT = NOW + timedelta(hours=3)
SHA = "a" * 40
TAG = "v1.0.1"
RELEASE_ID = "morva-1.0.1"


def public_file(key, path: Path):
    path.write_bytes(
        key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


def private_file(key, path: Path):
    path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


def signing_record(key, valid_from):
    public = key.public_key()
    return TrustedSigningKey(
        key_id=TrustedKeyRegistry.key_id_for(public),
        public_key_sha256=TrustedKeyRegistry.public_key_sha256_for(public),
        status="active",
        valid_from=valid_from,
    )


def write_release_sources(root: Path, registry_file: Path, bundle_signer):
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
        assessment_id="SEC-M3-50",
        assessed_at=NOW,
        scope_hash="c" * 64,
        required_controls=("authentication",),
        verified_controls=(),
    )
    certification = ReleaseCertification(RELEASE_ID, SHA, ("security-report",), ())
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

    evidence_files = []
    for path in (manifest_file, gate_file, rehearsal_file, registry_file):
        evidence_files.append(
            EvidenceFile(
                path.name,
                sha256(path.read_bytes()).hexdigest(),
                path.stat().st_size,
            )
        )
    bundle = ReleaseEvidenceBundle(
        RELEASE_ID,
        TAG,
        SHA,
        manifest.fingerprint,
        gate.fingerprint,
        rehearsal.fingerprint,
        "morva-signing",
        3,
        json.loads(registry_file.read_text(encoding="utf-8"))["registry"]["fingerprint"],
        tuple(evidence_files),
    ).sign(bundle_signer, VERIFY_AT)
    bundle_file = root / "bundle.json"
    bundle_file.write_text(
        json.dumps(
            {
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
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    bundle_public = root / "bundle-public.pem"
    public_file(bundle_signer, bundle_public)
    return manifest_file, gate_file, rehearsal_file, bundle_file, bundle_public, bundle


def make_fixture(root: Path):
    old_signer = Ed25519PrivateKey.generate()
    new_signer = Ed25519PrivateKey.generate()
    old_root = Ed25519PrivateKey.generate()
    new_root = Ed25519PrivateKey.generate()

    previous = TrustedKeyRegistry(
        "morva-signing",
        1,
        (signing_record(old_signer, NOW),),
    )
    replacement = signing_record(new_signer, SIGN_EFFECTIVE)
    intermediate = previous.rotate_key(
        TrustedKeyRegistry.key_id_for(old_signer.public_key()),
        replacement,
    )
    current = TrustedKeyRegistry(
        "morva-signing",
        3,
        intermediate.keys,
    )

    previous_signed = SignedTrustedKeyRegistry(previous).sign(old_root, NOW)
    intermediate_signed = SignedTrustedKeyRegistry(intermediate).sign(
        old_root, NOW + timedelta(minutes=1)
    )
    current_signed = SignedTrustedKeyRegistry(current).sign(
        new_root, ROOT_EFFECTIVE
    )

    sign_rotation = TrustRegistryRotationCeremony(
        "signing-rotation-001-002",
        "morva-signing",
        1,
        2,
        TrustedKeyRegistry.key_id_for(old_signer.public_key()),
        TrustedKeyRegistry.key_id_for(new_signer.public_key()),
        SIGN_EFFECTIVE,
        previous.fingerprint,
        intermediate.fingerprint,
        TrustedKeyRegistry.key_id_for(old_root.public_key()),
    )

    root_rotation = RootRotationCeremony.create(
        ceremony_id="root-rotation-002-003",
        registry_id="morva-signing",
        previous=intermediate_signed,
        current=current_signed,
        old_root_private_key=old_root,
        new_root_private_key=new_root,
        effective_at=ROOT_EFFECTIVE,
        transition_kind="scheduled_rotation",
        old_root_action="retire",
    )

    previous_file = root / "previous-registry.json"
    intermediate_file = root / "intermediate-registry.json"
    current_file = root / "current-registry.json"
    write_signed_registry(previous_signed, previous_file)
    write_signed_registry(intermediate_signed, intermediate_file)
    write_signed_registry(current_signed, current_file)

    sign_rotation_file = root / "signing-rotation.json"
    root_rotation_file = root / "root-rotation.json"
    write_signing_ceremony(sign_rotation, sign_rotation_file)
    write_root_ceremony(root_rotation, root_rotation_file)

    old_root_public = root / "old-root.pem"
    new_root_public = root / "new-root.pem"
    public_file(old_root, old_root_public)
    public_file(new_root, new_root_public)

    manifest, gate, rehearsal, bundle, bundle_public, bundle_obj = write_release_sources(
        root,
        current_file,
        new_signer,
    )
    return {
        "previous": previous,
        "intermediate": intermediate,
        "current": current,
        "sign_rotation": sign_rotation,
        "root_rotation": root_rotation,
        "old_root": old_root,
        "new_root": new_root,
        "new_signer": new_signer,
        "files": (manifest, gate, rehearsal, bundle, bundle_public),
        "registry_files": (previous_file, intermediate_file, current_file),
        "ceremony_files": (sign_rotation_file, root_rotation_file),
        "root_public_files": (old_root_public, new_root_public),
        "bundle": bundle_obj,
    }


def test_full_trust_chain_verifies(tmp_path: Path):
    fixture = make_fixture(tmp_path)
    manifest, gate, rehearsal, bundle, bundle_public = fixture["files"]
    previous, intermediate, current = fixture["registry_files"]
    sign_rotation, root_rotation = fixture["ceremony_files"]
    old_root, new_root = fixture["root_public_files"]

    result = verify_chain(
        bundle_file=bundle,
        manifest_file=manifest,
        gate_file=gate,
        rehearsal_file=rehearsal,
        public_key_file=bundle_public,
        previous_registry_file=previous,
        intermediate_registry_file=intermediate,
        current_registry_file=current,
        signing_key_rotation_file=sign_rotation,
        root_rotation_file=root_rotation,
        old_root_public_key_file=old_root,
        new_root_public_key_file=new_root,
        root=tmp_path,
        expected_sha=SHA,
        verified_at=VERIFY_AT,
    )
    assert result.release_id == RELEASE_ID
    assert result.tag == TAG
    assert result.candidate_sha == SHA
    assert len(result.fingerprint) == 64


def test_chain_rejects_wrong_intermediate_registry(tmp_path: Path):
    fixture = make_fixture(tmp_path)
    manifest, gate, rehearsal, bundle, bundle_public = fixture["files"]
    previous, _, current = fixture["registry_files"]
    sign_rotation, root_rotation = fixture["ceremony_files"]
    old_root, new_root = fixture["root_public_files"]
    wrong = TrustedKeyRegistry("morva-signing", 99, fixture["intermediate"].keys)
    wrong_file = tmp_path / "wrong.json"
    wrong_signed = SignedTrustedKeyRegistry(wrong).sign(fixture["old_root"], NOW)
    write_signed_registry(wrong_signed, wrong_file)

    with pytest.raises((TrustChainVerificationError, ValueError)):
        verify_chain(
            bundle_file=bundle,
            manifest_file=manifest,
            gate_file=gate,
            rehearsal_file=rehearsal,
            public_key_file=bundle_public,
            previous_registry_file=previous,
            intermediate_registry_file=wrong_file,
            current_registry_file=current,
            signing_key_rotation_file=sign_rotation,
            root_rotation_file=root_rotation,
            old_root_public_key_file=old_root,
            new_root_public_key_file=new_root,
            root=tmp_path,
            expected_sha=SHA,
            verified_at=VERIFY_AT,
        )


def test_chain_rejects_release_bundle_bound_to_wrong_registry(tmp_path: Path):
    fixture = make_fixture(tmp_path)
    result_bundle = fixture["bundle"]
    wrong = json.loads((tmp_path / "current-registry.json").read_text(encoding="utf-8"))
    result_bundle_payload = json.loads((tmp_path / "bundle.json").read_text(encoding="utf-8"))
    result_bundle_payload["registry_fingerprint"] = wrong["registry"]["fingerprint"][:-1] + "0"
    (tmp_path / "bundle.json").write_text(
        json.dumps(result_bundle_payload, sort_keys=True),
        encoding="utf-8",
    )
    manifest, gate, rehearsal, bundle, bundle_public = fixture["files"]
    previous, intermediate, current = fixture["registry_files"]
    sign_rotation, root_rotation = fixture["ceremony_files"]
    old_root, new_root = fixture["root_public_files"]
    with pytest.raises(Exception):
        verify_chain(
            bundle_file=bundle,
            manifest_file=manifest,
            gate_file=gate,
            rehearsal_file=rehearsal,
            public_key_file=bundle_public,
            previous_registry_file=previous,
            intermediate_registry_file=intermediate,
            current_registry_file=current,
            signing_key_rotation_file=sign_rotation,
            root_rotation_file=root_rotation,
            old_root_public_key_file=old_root,
            new_root_public_key_file=new_root,
            root=tmp_path,
            expected_sha=SHA,
            verified_at=VERIFY_AT,
        )


def test_chain_fingerprint_changes_when_bundle_changes(tmp_path: Path):
    fixture = make_fixture(tmp_path)
    verification = verify_trust_chain(
        previous=SignedTrustedKeyRegistry(fixture["previous"]).sign(
            fixture["old_root"], NOW
        ),
        intermediate=SignedTrustedKeyRegistry(fixture["intermediate"]).sign(
            fixture["old_root"], NOW + timedelta(minutes=1)
        ),
        current=SignedTrustedKeyRegistry(fixture["current"]).sign(
            fixture["new_root"], ROOT_EFFECTIVE
        ),
        signing_key_rotation=fixture["sign_rotation"],
        root_rotation=fixture["root_rotation"],
        release_bundle=fixture["bundle"],
        release_signing_public_key=fixture["new_signer"].public_key(),
        old_root_public_key=fixture["old_root"].public_key(),
        new_root_public_key=fixture["new_root"].public_key(),
        verified_at=VERIFY_AT,
    )
    changed = ReleaseEvidenceBundle(
        fixture["bundle"].release_id,
        fixture["bundle"].tag,
        fixture["bundle"].candidate_sha,
        fixture["bundle"].manifest_fingerprint,
        fixture["bundle"].gate_fingerprint,
        fixture["bundle"].rehearsal_fingerprint,
        fixture["bundle"].registry_id,
        fixture["bundle"].registry_version,
        fixture["bundle"].registry_fingerprint,
        fixture["bundle"].evidence_files,
        fixture["bundle"].signature,
    )
    assert verification.fingerprint != changed.fingerprint
