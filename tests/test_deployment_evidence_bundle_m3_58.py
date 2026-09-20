from __future__ import annotations

import json
from pathlib import Path

import pytest

from morva.runtime.deployment_evidence_bundle import (
    DeploymentEvidenceBundleError,
    build_deployment_evidence_bundle,
    verify_deployment_evidence_bundle,
)
from morva.runtime.deployment_evidence_verifier import (
    verify_deployment_evidence,
    write_verification_receipt,
)
from morva.runtime.release_deployment_evidence import (
    build_deployment_evidence_gate,
)
from tests.test_release_deployment_evidence_m3_56 import (
    _attestation,
    _receipt,
)

REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"
SHA = "a" * 40


def _inputs(monkeypatch, tmp_path: Path):
    receipt = _receipt(monkeypatch, tmp_path / "source")
    attestation = _attestation(receipt)
    gate = build_deployment_evidence_gate(
        receipt=receipt,
        attestation=attestation,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    receipt_file = tmp_path / "release-receipt.json"
    gate_file = tmp_path / "deployment-gate.json"
    attestation_file = tmp_path / "attestation.json"
    verification_file = tmp_path / "verification.json"
    receipt_file.write_text(
        json.dumps(receipt.to_payload(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    gate_file.write_text(
        json.dumps(gate.to_payload(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    attestation_file.write_text(
        json.dumps(
            {
                "attestation_version": 1,
                "evidence_id": attestation.evidence_id,
                "release_receipt_fingerprint": (
                    attestation.release_receipt_fingerprint
                ),
                "environment": attestation.environment,
                "deployment_id": attestation.deployment_id,
                "deployment_status": attestation.deployment_status,
                "deployed_sha": attestation.deployed_sha,
                "deployed_at": attestation.deployed_at,
                "operator": attestation.operator,
                "healthcheck_sha256": attestation.healthcheck_sha256,
                "rollback_target_sha": attestation.rollback_target_sha,
                "rollback_verified": attestation.rollback_verified,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    verification = verify_deployment_evidence(
        gate_file=gate_file,
        release_receipt_file=receipt_file,
        attestation_file=attestation_file,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    write_verification_receipt(verification, verification_file)
    return receipt_file, gate_file, attestation_file, verification_file


def test_bundle_roundtrip(monkeypatch, tmp_path: Path):
    receipt, gate, attestation, verification = _inputs(
        monkeypatch,
        tmp_path / "input",
    )
    archive = tmp_path / "bundle.tar.gz"
    metadata = tmp_path / "bundle.json"
    bundle = build_deployment_evidence_bundle(
        release_receipt_file=receipt,
        deployment_gate_file=gate,
        attestation_file=attestation,
        deployment_verification_receipt_file=verification,
        output_archive=archive,
        metadata_file=metadata,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    verified = verify_deployment_evidence_bundle(
        archive_path=archive,
        metadata_file=metadata,
        expected_repository=REPOSITORY,
        expected_tag=TAG,
        expected_sha=SHA,
    )
    assert bundle.bundle_id == verified.bundle_id
    assert len(bundle.source_manifest) == 4


def test_bundle_archive_is_deterministic(monkeypatch, tmp_path: Path):
    first = _inputs(monkeypatch, tmp_path / "first")
    first_archive = tmp_path / "first" / "bundle.tar.gz"
    first_meta = tmp_path / "first" / "bundle.json"
    second_archive = tmp_path / "second" / "bundle.tar.gz"
    second_meta = tmp_path / "second" / "bundle.json"
    first_archive.parent.mkdir(parents=True, exist_ok=True)
    second_archive.parent.mkdir(parents=True, exist_ok=True)
    second = first
    first_bundle = build_deployment_evidence_bundle(
        release_receipt_file=first[0],
        deployment_gate_file=first[1],
        attestation_file=first[2],
        deployment_verification_receipt_file=first[3],
        output_archive=first_archive,
        metadata_file=first_meta,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    second_bundle = build_deployment_evidence_bundle(
        release_receipt_file=second[0],
        deployment_gate_file=second[1],
        attestation_file=second[2],
        deployment_verification_receipt_file=second[3],
        output_archive=second_archive,
        metadata_file=second_meta,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    assert first_bundle.bundle_fingerprint == second_bundle.bundle_fingerprint
    assert first_archive.read_bytes() == second_archive.read_bytes()


def test_bundle_rejects_archive_tamper(monkeypatch, tmp_path: Path):
    inputs = _inputs(monkeypatch, tmp_path / "input")
    archive = tmp_path / "bundle.tar.gz"
    metadata = tmp_path / "bundle.json"
    build_deployment_evidence_bundle(
        release_receipt_file=inputs[0],
        deployment_gate_file=inputs[1],
        attestation_file=inputs[2],
        deployment_verification_receipt_file=inputs[3],
        output_archive=archive,
        metadata_file=metadata,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    archive.write_bytes(archive.read_bytes() + b"tamper")
    with pytest.raises(
        DeploymentEvidenceBundleError,
        match="SHA-256 mismatch",
    ):
        verify_deployment_evidence_bundle(
            archive_path=archive,
            metadata_file=metadata,
            expected_repository=REPOSITORY,
            expected_tag=TAG,
            expected_sha=SHA,
        )


def test_bundle_rejects_private_key_material(tmp_path: Path):
    from morva.runtime.deployment_evidence_bundle import _hash_file

    path = tmp_path / "attestation.json"
    path.write_bytes(b"-----BEGIN " + b"PRIVATE KEY-----")
    with pytest.raises(DeploymentEvidenceBundleError, match="private-key"):
        _hash_file(path)


def test_bundle_outputs_are_write_once(monkeypatch, tmp_path: Path):
    inputs = _inputs(monkeypatch, tmp_path / "input")
    archive = tmp_path / "bundle.tar.gz"
    metadata = tmp_path / "bundle.json"
    kwargs = {
        "release_receipt_file": inputs[0],
        "deployment_gate_file": inputs[1],
        "attestation_file": inputs[2],
        "deployment_verification_receipt_file": inputs[3],
        "output_archive": archive,
        "metadata_file": metadata,
        "repository": REPOSITORY,
        "tag": TAG,
        "candidate_sha": SHA,
    }
    build_deployment_evidence_bundle(**kwargs)
    with pytest.raises(DeploymentEvidenceBundleError, match="write-once"):
        build_deployment_evidence_bundle(**kwargs)
