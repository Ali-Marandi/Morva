from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from dataclasses import replace

import pytest

from morva.runtime.adapter_activation_gate import (
    AdapterActivationAuthorization,
    build_activation_gate,
)
from morva.runtime.independent_adapter_activation_verifier import (
    IndependentAdapterActivationVerificationError,
    verify_adapter_activation,
    write_receipt,
)
from tests.test_adapter_activation_gate_m3_77 import (
    REPOSITORY,
    SHA,
    CHECKED_AT,
    _auth,
    _registry_file,
)


def _gate_files(tmp_path: Path):
    registry, fingerprint = _registry_file(tmp_path)
    gate = build_activation_gate(
        registry_file=registry,
        authorization=_auth(fingerprint),
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )
    path = tmp_path / "activation-gate.json"
    path.write_text(
        json.dumps(gate.to_payload()) + "\n",
        encoding="utf-8",
    )
    return registry, path, gate


def test_roundtrip(tmp_path: Path):
    registry, gate, _ = _gate_files(tmp_path)
    receipt = verify_adapter_activation(
        registry_file=registry,
        activation_gate=gate,
        repository=REPOSITORY,
        candidate_sha=SHA,
    )
    assert receipt.adapters


def test_gate_tamper_is_rejected(tmp_path: Path):
    registry, gate, original = _gate_files(tmp_path)
    payload = json.loads(gate.read_text(encoding="utf-8"))
    payload["approver"] = "tampered"
    payload["fingerprint"] = original.fingerprint
    gate.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentAdapterActivationVerificationError,
        match="fingerprint mismatch",
    ):
        verify_adapter_activation(
            registry_file=registry,
            activation_gate=gate,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_registry_binding_is_rechecked(tmp_path: Path):
    registry, gate, _ = _gate_files(tmp_path)
    payload = json.loads(gate.read_text(encoding="utf-8"))
    payload["registry_fingerprint"] = "0" * 64
    registry_fingerprint = payload["registry_fingerprint"]
    from morva.runtime.adapter_activation_gate import AdapterActivationGate

    candidate = AdapterActivationGate(
        gate_version=payload["gate_version"],
        repository=payload["repository"],
        candidate_sha=payload["candidate_sha"],
        registry_fingerprint=registry_fingerprint,
        authorization_id=payload["authorization_id"],
        approver=payload["approver"],
        target_environment=payload["target_environment"],
        adapters=tuple(payload["adapters"]),
        approved_at=payload["approved_at"],
        checked_at=datetime.fromisoformat(payload["checked_at"]),
    )
    payload["fingerprint"] = candidate.fingerprint
    gate.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentAdapterActivationVerificationError,
        match="registry fingerprint",
    ):
        verify_adapter_activation(
            registry_file=registry,
            activation_gate=gate,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_future_approval_is_rejected(tmp_path: Path):
    registry, gate, original = _gate_files(tmp_path)
    future_gate = replace(
        original,
        approved_at="2026-09-20T04:00:00+00:00",
    )
    payload = future_gate.to_payload()
    gate.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentAdapterActivationVerificationError,
        match="future",
    ):
        verify_adapter_activation(
            registry_file=registry,
            activation_gate=gate,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_receipt_write_once(tmp_path: Path):
    registry, gate, _ = _gate_files(tmp_path)
    receipt = verify_adapter_activation(
        registry_file=registry,
        activation_gate=gate,
        repository=REPOSITORY,
        candidate_sha=SHA,
    )
    output = tmp_path / "receipt.json"
    write_receipt(receipt, output)
    with pytest.raises(
        IndependentAdapterActivationVerificationError,
        match="write-once",
    ):
        write_receipt(receipt, output)
