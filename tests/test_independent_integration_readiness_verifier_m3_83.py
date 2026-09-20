from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from dataclasses import replace

import pytest

from morva.runtime.adapter_activation_gate import build_activation_gate
from morva.runtime.independent_adapter_activation_verifier import (
    verify_adapter_activation,
    write_receipt,
)
from morva.runtime.independent_integration_contract_verifier import (
    verify_integration_contract,
    write_receipt as write_contract_receipt,
)
from morva.runtime.integration_contract_manifest import build_manifest, write_manifest
from morva.runtime.integration_readiness_gate import build_integration_readiness_gate, write_gate
from morva.runtime.independent_integration_readiness_verifier import (
    IndependentIntegrationReadinessVerificationError,
    verify_integration_readiness,
    write_receipt as write_readiness_receipt,
)
from tests.test_adapter_activation_gate_m3_77 import (
    CHECKED_AT,
    REPOSITORY,
    SHA,
    _auth,
    _registry_file,
)


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
        json.dumps(activation.to_payload()) + "\n",
        encoding="utf-8",
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

    readiness = build_integration_readiness_gate(
        registry_file=registry,
        activation_gate=activation_file,
        activation_verification_receipt=activation_receipt_file,
        contract_manifest=manifest_file,
        contract_verification_receipt=contract_receipt_file,
        repository=REPOSITORY,
        candidate_sha=SHA,
        target_environment="staging",
        checked_at=datetime.fromisoformat("2026-09-20T03:00:00+00:00"),
    )
    readiness_file = tmp_path / "readiness.json"
    write_gate(readiness, readiness_file)
    return (
        registry,
        activation_file,
        manifest_file,
        readiness_file,
    )


def test_roundtrip(tmp_path: Path):
    registry, activation, manifest, readiness = _fixtures(tmp_path)
    receipt = verify_integration_readiness(
        registry_file=registry,
        activation_gate=activation,
        contract_manifest=manifest,
        readiness_gate=readiness,
        repository=REPOSITORY,
        candidate_sha=SHA,
    )
    assert receipt.adapters


def test_gate_tamper_is_rejected(tmp_path: Path):
    registry, activation, manifest, readiness = _fixtures(tmp_path)
    payload = json.loads(readiness.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "f" * 40
    readiness.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentIntegrationReadinessVerificationError,
        match="fingerprint mismatch|candidate SHA",
    ):
        verify_integration_readiness(
            registry_file=registry,
            activation_gate=activation,
            contract_manifest=manifest,
            readiness_gate=readiness,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_contract_change_is_rejected(tmp_path: Path):
    registry, activation, manifest, readiness = _fixtures(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["adapters"][0]["operations"][0] = "tampered"
    manifest.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentIntegrationReadinessVerificationError,
        match="integration contract",
    ):
        verify_integration_readiness(
            registry_file=registry,
            activation_gate=activation,
            contract_manifest=manifest,
            readiness_gate=readiness,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_receipt_write_once(tmp_path: Path):
    registry, activation, manifest, readiness = _fixtures(tmp_path)
    receipt = verify_integration_readiness(
        registry_file=registry,
        activation_gate=activation,
        contract_manifest=manifest,
        readiness_gate=readiness,
        repository=REPOSITORY,
        candidate_sha=SHA,
    )
    output = tmp_path / "verification.json"
    write_readiness_receipt(receipt, output)
    with pytest.raises(
        IndependentIntegrationReadinessVerificationError,
        match="write-once",
    ):
        write_readiness_receipt(receipt, output)
