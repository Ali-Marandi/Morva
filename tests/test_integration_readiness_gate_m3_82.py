from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.adapter_activation_gate import AdapterActivationAuthorization, build_activation_gate
from morva.runtime.independent_adapter_activation_verifier import verify_adapter_activation, write_receipt
from morva.runtime.independent_integration_contract_verifier import verify_integration_contract, write_receipt as write_contract_receipt
from morva.runtime.integration_contract_manifest import build_manifest, write_manifest
from morva.runtime.integration_readiness_gate import (
    IntegrationReadinessGateError,
    build_integration_readiness_gate,
    write_gate,
)
from tests.test_adapter_activation_gate_m3_77 import REPOSITORY, SHA, CHECKED_AT, _auth, _registry_file


def _fixtures(tmp_path: Path):
    registry, fingerprint = _registry_file(tmp_path)
    activation = build_activation_gate(
        registry_file=registry,
        authorization=_auth(fingerprint),
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )
    activation_file = tmp_path / "activation.json"
    activation_file.write_text(
        json.dumps(activation.to_payload()) + "\n", encoding="utf-8"
    )
    activation_receipt = verify_adapter_activation(
        registry_file=registry,
        activation_gate=activation_file,
        repository=REPOSITORY,
        candidate_sha=SHA,
    )
    activation_receipt_file = tmp_path / "activation-receipt.json"
    write_receipt(activation_receipt, activation_receipt_file)

    manifest = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at="2026-09-20T02:00:00+00:00",
    )
    manifest_file = tmp_path / "manifest.json"
    write_manifest(manifest, manifest_file)
    contract_receipt = verify_integration_contract(
        manifest_file=manifest_file,
        repository=REPOSITORY,
        candidate_sha=SHA,
    )
    contract_receipt_file = tmp_path / "contract-receipt.json"
    write_contract_receipt(contract_receipt, contract_receipt_file)
    return registry, activation_file, activation_receipt_file, manifest_file, contract_receipt_file


def test_roundtrip(tmp_path: Path):
    sources = _fixtures(tmp_path)
    gate = build_integration_readiness_gate(
        registry_file=sources[0],
        activation_gate=sources[1],
        activation_verification_receipt=sources[2],
        contract_manifest=sources[3],
        contract_verification_receipt=sources[4],
        repository=REPOSITORY,
        candidate_sha=SHA,
        target_environment="staging",
        checked_at=datetime.fromisoformat("2026-09-20T03:00:00+00:00"),
    )
    assert gate.adapter_registry_fingerprint


def test_stored_receipt_tamper_is_rejected(tmp_path: Path):
    sources = _fixtures(tmp_path)
    payload = json.loads(sources[2].read_text(encoding="utf-8"))
    payload["approver"] = "tampered"
    sources[2].write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(IntegrationReadinessGateError, match="M3.78"):
        build_integration_readiness_gate(
            registry_file=sources[0],
            activation_gate=sources[1],
            activation_verification_receipt=sources[2],
            contract_manifest=sources[3],
            contract_verification_receipt=sources[4],
            repository=REPOSITORY,
            candidate_sha=SHA,
            target_environment="staging",
            checked_at=datetime.fromisoformat("2026-09-20T03:00:00+00:00"),
        )


def test_contract_receipt_tamper_is_rejected(tmp_path: Path):
    sources = _fixtures(tmp_path)
    payload = json.loads(sources[4].read_text(encoding="utf-8"))
    payload["manifest_fingerprint"] = "0" * 64
    sources[4].write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(IntegrationReadinessGateError, match="M3.81"):
        build_integration_readiness_gate(
            registry_file=sources[0],
            activation_gate=sources[1],
            activation_verification_receipt=sources[2],
            contract_manifest=sources[3],
            contract_verification_receipt=sources[4],
            repository=REPOSITORY,
            candidate_sha=SHA,
            target_environment="staging",
            checked_at=datetime.fromisoformat("2026-09-20T03:00:00+00:00"),
        )


def test_write_once(tmp_path: Path):
    sources = _fixtures(tmp_path)
    gate = build_integration_readiness_gate(
        registry_file=sources[0],
        activation_gate=sources[1],
        activation_verification_receipt=sources[2],
        contract_manifest=sources[3],
        contract_verification_receipt=sources[4],
        repository=REPOSITORY,
        candidate_sha=SHA,
        target_environment="pilot",
        checked_at=datetime.fromisoformat("2026-09-20T03:00:00+00:00"),
    )
    out = tmp_path / "gate.json"
    write_gate(gate, out)
    with pytest.raises(IntegrationReadinessGateError, match="write-once"):
        write_gate(gate, out)
