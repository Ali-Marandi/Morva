from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from morva.runtime.production_boundary_policy import (
    ProductionBoundaryPolicyReceipt,
    write_receipt as write_policy_receipt,
)
from morva.runtime.technical_readiness_gate import (
    REQUIRED_POLICY_PATHS,
    TechnicalReadinessGateError,
    build_technical_readiness_gate,
    load_policy_receipt,
    write_gate,
)
from tests.test_production_promotion_verifier_m3_60 import _inputs


REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"
SHA = "a" * 40


def _ready_inputs(monkeypatch, tmp_path: Path):
    bundle, metadata, promotion_gate, authorization, attestation = _inputs(
        monkeypatch,
        tmp_path,
    )
    policy = ProductionBoundaryPolicyReceipt(
        policy_version=1,
        repository=REPOSITORY,
        scanned_paths=REQUIRED_POLICY_PATHS,
        findings=(),
        verified_at=datetime.now(timezone.utc),
    )
    policy_file = tmp_path / "policy.json"
    write_policy_receipt(policy, policy_file)
    return bundle, metadata, promotion_gate, authorization, attestation, policy_file


def test_readiness_gate_roundtrip(monkeypatch, tmp_path: Path):
    inputs = _ready_inputs(monkeypatch, tmp_path)
    output = tmp_path / "readiness.json"
    gate = build_technical_readiness_gate(
        bundle_archive=inputs[0],
        bundle_metadata=inputs[1],
        promotion_gate=inputs[2],
        authorization=inputs[3],
        deployment_attestation=inputs[4],
        policy_receipt=inputs[5],
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    write_gate(gate, output)
    assert gate.target_environment == "production"
    assert gate.policy_passed
    with pytest.raises(TechnicalReadinessGateError, match="write-once"):
        write_gate(gate, output)


def test_policy_receipt_tamper_is_rejected(monkeypatch, tmp_path: Path):
    inputs = _ready_inputs(monkeypatch, tmp_path)
    payload = json.loads(inputs[5].read_text(encoding="utf-8"))
    payload["findings"] = [{"path": "tampered", "rule": "tamper", "detail": "tampered"}]
    inputs[5].write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TechnicalReadinessGateError, match="fingerprint mismatch"):
        load_policy_receipt(inputs[5])


def test_incomplete_policy_coverage_is_rejected(
    monkeypatch,
    tmp_path: Path,
):
    inputs = _ready_inputs(monkeypatch, tmp_path)
    policy = ProductionBoundaryPolicyReceipt(
        policy_version=1,
        repository=REPOSITORY,
        scanned_paths=REQUIRED_POLICY_PATHS[:-1],
        findings=(),
        verified_at=datetime.now(timezone.utc),
    )
    policy_file = tmp_path / "policy-incomplete.json"
    write_policy_receipt(policy, policy_file)
    with pytest.raises(
        TechnicalReadinessGateError,
        match="complete",
    ):
        build_technical_readiness_gate(
            bundle_archive=inputs[0],
            bundle_metadata=inputs[1],
            promotion_gate=inputs[2],
            authorization=inputs[3],
            deployment_attestation=inputs[4],
            policy_receipt=policy_file,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )
