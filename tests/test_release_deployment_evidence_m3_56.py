from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

import pytest

from morva.runtime.release_deployment_evidence import (
    DeploymentEvidenceAttestation,
    DeploymentEvidenceGateError,
    build_deployment_evidence_gate,
    load_release_receipt,
    write_gate,
)
from morva.runtime.release_post_publication import ReleasePostPublicationReceipt
from tests.test_release_post_publication_verifier_m3_55 import (
    _mock_runner,
    _release_payload,
)
from tests.test_release_publication_gate_m3_53 import build_test_gate


SHA = "a" * 40
REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"


def _receipt(monkeypatch, tmp_path: Path) -> ReleasePostPublicationReceipt:
    _, gate, gate_file, archive, metadata = build_test_gate(tmp_path)
    release = _release_payload(
        gate_file=gate_file,
        archive=archive,
        metadata=metadata,
        name=gate.release_id,
    )
    _, run = _mock_runner(release)
    monkeypatch.setattr(
        "morva.runtime.release_post_publication._run",
        run,
    )
    from morva.runtime.release_post_publication import verify_published_release

    return verify_published_release(
        gate_file=gate_file,
        archive_path=archive,
        artifact_metadata=metadata,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )


def _attestation(receipt, **overrides):
    payload = {
        "attestation_version": 1,
        "evidence_id": "DEP-001",
        "release_receipt_fingerprint": receipt.fingerprint,
        "environment": "staging",
        "deployment_id": "deploy-001",
        "deployment_status": "succeeded",
        "deployed_sha": SHA,
        "deployed_at": "2026-09-19T23:10:00+00:00",
        "operator": "release-operator",
        "healthcheck_sha256": sha256(b"healthy").hexdigest(),
        "rollback_target_sha": "b" * 40,
        "rollback_verified": True,
    }
    payload.update(overrides)
    return DeploymentEvidenceAttestation(**payload)


def test_build_gate_binds_release_receipt_and_sha(monkeypatch, tmp_path: Path):
    receipt = _receipt(monkeypatch, tmp_path / "receipt")
    attestation = _attestation(receipt)
    gate = build_deployment_evidence_gate(
        receipt=receipt,
        attestation=attestation,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    assert gate.post_publication_fingerprint == receipt.fingerprint
    assert gate.deployed_sha == SHA
    assert gate.environment == "staging"


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("release_receipt_fingerprint", "0" * 64, "not bound"),
        ("deployed_sha", "b" * 40, "deployed SHA"),
    ],
)
def test_gate_rejects_mismatched_binding(
    monkeypatch,
    tmp_path: Path,
    field: str,
    value: str,
    match: str,
):
    receipt = _receipt(monkeypatch, tmp_path / "receipt")
    attestation = _attestation(receipt, **{field: value})
    with pytest.raises(DeploymentEvidenceGateError, match=match):
        build_deployment_evidence_gate(
            receipt=receipt,
            attestation=attestation,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_gate_rejects_unverified_rollback(monkeypatch, tmp_path: Path):
    receipt = _receipt(monkeypatch, tmp_path / "receipt")
    attestation = _attestation(receipt, rollback_verified=False)
    with pytest.raises(DeploymentEvidenceGateError, match="rollback verification"):
        build_deployment_evidence_gate(
            receipt=receipt,
            attestation=attestation,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_load_release_receipt_detects_tampering(monkeypatch, tmp_path: Path):
    receipt_dir = tmp_path / "receipt"
    receipt = _receipt(monkeypatch, receipt_dir)
    output = receipt_dir / "receipt.json"
    output.write_text(
        json.dumps(receipt.to_payload(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    payload["release_id"] = "tampered"
    output.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(DeploymentEvidenceGateError, match="fingerprint mismatch"):
        load_release_receipt(output)


def test_write_gate_is_write_once(monkeypatch, tmp_path: Path):
    receipt = _receipt(monkeypatch, tmp_path / "receipt")
    gate = build_deployment_evidence_gate(
        receipt=receipt,
        attestation=_attestation(receipt),
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    output = tmp_path / "gate.json"
    write_gate(gate, output)
    with pytest.raises(DeploymentEvidenceGateError, match="write-once"):
        write_gate(gate, output)


def test_gate_fingerprint_is_stable(monkeypatch, tmp_path: Path):
    receipt = _receipt(monkeypatch, tmp_path / "receipt")
    attestation = _attestation(receipt)
    first = build_deployment_evidence_gate(
        receipt=receipt,
        attestation=attestation,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    second = build_deployment_evidence_gate(
        receipt=receipt,
        attestation=attestation,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    assert first.fingerprint == second.fingerprint
