from __future__ import annotations

import json
from pathlib import Path

import pytest

from morva.runtime.deployment_evidence_verifier import (
    DeploymentEvidenceGateError,
    verify_deployment_evidence,
    write_verification_receipt,
)
from morva.runtime.release_deployment_evidence import (
    build_deployment_evidence_gate,
    load_attestation,
)
from tests.test_release_deployment_evidence_m3_56 import _attestation, _receipt


SHA = "a" * 40
REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"


def _build_inputs(monkeypatch, tmp_path: Path):
    receipt = _receipt(monkeypatch, tmp_path / "receipt")
    attestation = _attestation(receipt)
    gate = build_deployment_evidence_gate(
        receipt=receipt,
        attestation=attestation,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    gate_file = tmp_path / "deployment-gate.json"
    release_receipt_file = tmp_path / "release-receipt.json"
    attestation_file = tmp_path / "attestation.json"
    from morva.runtime.release_deployment_evidence import (
        write_gate,
    )

    receipt_payload = receipt.to_payload()
    release_receipt_file.write_text(
        json.dumps(receipt_payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    attestation_payload = {
        "attestation_version": 1,
        "evidence_id": attestation.evidence_id,
        "release_receipt_fingerprint": attestation.release_receipt_fingerprint,
        "environment": attestation.environment,
        "deployment_id": attestation.deployment_id,
        "deployment_status": attestation.deployment_status,
        "deployed_sha": attestation.deployed_sha,
        "deployed_at": attestation.deployed_at,
        "operator": attestation.operator,
        "healthcheck_sha256": attestation.healthcheck_sha256,
        "rollback_target_sha": attestation.rollback_target_sha,
        "rollback_verified": attestation.rollback_verified,
    }
    attestation_file.write_text(
        json.dumps(attestation_payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    write_gate(gate, gate_file)
    return gate, gate_file, release_receipt_file, attestation_file


def test_independent_verifier_roundtrip(monkeypatch, tmp_path: Path):
    gate, gate_file, receipt_file, attestation_file = _build_inputs(
        monkeypatch,
        tmp_path,
    )
    receipt = verify_deployment_evidence(
        gate_file=gate_file,
        release_receipt_file=receipt_file,
        attestation_file=attestation_file,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    assert receipt.deployment_gate_fingerprint == gate.fingerprint
    assert receipt.environment == "staging"


def test_verifier_rejects_gate_tampering(monkeypatch, tmp_path: Path):
    _, gate_file, receipt_file, attestation_file = _build_inputs(
        monkeypatch,
        tmp_path,
    )
    payload = json.loads(gate_file.read_text(encoding="utf-8"))
    payload["deployment_id"] = "tampered"
    gate_file.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        DeploymentEvidenceGateError,
        match="fingerprint mismatch",
    ):
        verify_deployment_evidence(
            gate_file=gate_file,
            release_receipt_file=receipt_file,
            attestation_file=attestation_file,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_verifier_rejects_attestation_binding_change(monkeypatch, tmp_path: Path):
    _, gate_file, receipt_file, attestation_file = _build_inputs(
        monkeypatch,
        tmp_path,
    )
    payload = json.loads(attestation_file.read_text(encoding="utf-8"))
    payload["deployment_id"] = "different-deployment"
    attestation_file.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        DeploymentEvidenceGateError,
        match="does not match receipt and attestation",
    ):
        verify_deployment_evidence(
            gate_file=gate_file,
            release_receipt_file=receipt_file,
            attestation_file=attestation_file,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_verifier_rejects_receipt_tampering(monkeypatch, tmp_path: Path):
    _, gate_file, receipt_file, attestation_file = _build_inputs(
        monkeypatch,
        tmp_path,
    )
    payload = json.loads(receipt_file.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "b" * 40
    receipt_file.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        DeploymentEvidenceGateError,
        match="fingerprint mismatch",
    ):
        verify_deployment_evidence(
            gate_file=gate_file,
            release_receipt_file=receipt_file,
            attestation_file=attestation_file,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_verifier_is_write_once(monkeypatch, tmp_path: Path):
    _, gate_file, receipt_file, attestation_file = _build_inputs(
        monkeypatch,
        tmp_path,
    )
    receipt = verify_deployment_evidence(
        gate_file=gate_file,
        release_receipt_file=receipt_file,
        attestation_file=attestation_file,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    output = tmp_path / "verification.json"
    write_verification_receipt(receipt, output)
    with pytest.raises(DeploymentEvidenceGateError, match="write-once"):
        write_verification_receipt(receipt, output)


def test_attestation_loader_rejects_wrong_sha(tmp_path: Path):
    path = tmp_path / "attestation.json"
    path.write_text(
        json.dumps(
            {
                "attestation_version": 1,
                "evidence_id": "DEP-003",
                "release_receipt_fingerprint": "0" * 64,
                "environment": "staging",
                "deployment_id": "deploy-003",
                "deployment_status": "succeeded",
                "deployed_sha": "z" * 40,
                "deployed_at": "2026-09-19T23:10:00+00:00",
                "operator": "operator",
                "healthcheck_sha256": "0" * 64,
                "rollback_target_sha": "b" * 40,
                "rollback_verified": True,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(DeploymentEvidenceGateError, match="structure"):
        load_attestation(path)
