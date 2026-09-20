from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from morva.runtime.independent_integration_execution_readiness_verifier import (
    IndependentIntegrationExecutionReadinessVerificationError,
    verify_execution_readiness,
    write_receipt,
)
from morva.runtime.integration_execution_readiness_gate import (
    build_integration_execution_readiness_gate,
    write_gate,
)
from tests.test_independent_integration_execution_verifier_m3_85 import _sources


def _sources_with_gate(tmp_path: Path):
    execution, readiness, verification, registry, activation, manifest = _sources(tmp_path)
    gate = build_integration_execution_readiness_gate(
        execution_evidence=execution,
        readiness_gate=readiness,
        readiness_verification_receipt=verification,
        registry_file=registry,
        activation_gate=activation,
        contract_manifest=manifest,
        repository="Ali-Marandi/Morva",
        candidate_sha="a" * 40,
        checked_at=datetime.fromisoformat("2026-09-20T11:00:00+00:00"),
        max_execution_age_hours=24,
    )
    gate_file = tmp_path / "execution-readiness.json"
    write_gate(gate, gate_file)
    return execution, readiness, verification, registry, activation, manifest, gate_file


def test_roundtrip(tmp_path: Path):
    sources = _sources_with_gate(tmp_path)
    receipt = verify_execution_readiness(
        execution_evidence=sources[0],
        readiness_gate=sources[1],
        readiness_verification_receipt=sources[2],
        registry_file=sources[3],
        activation_gate=sources[4],
        contract_manifest=sources[5],
        execution_readiness_gate=sources[6],
        repository="Ali-Marandi/Morva",
        candidate_sha="a" * 40,
    )
    assert receipt.execution_readiness_gate_fingerprint


def test_gate_tamper_is_rejected(tmp_path: Path):
    sources = _sources_with_gate(tmp_path)
    payload = json.loads(sources[6].read_text(encoding="utf-8"))
    payload["candidate_sha"] = "f" * 40
    sources[6].write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentIntegrationExecutionReadinessVerificationError,
        match="fingerprint mismatch",
    ):
        verify_execution_readiness(
            execution_evidence=sources[0],
            readiness_gate=sources[1],
            readiness_verification_receipt=sources[2],
            registry_file=sources[3],
            activation_gate=sources[4],
            contract_manifest=sources[5],
            execution_readiness_gate=sources[6],
            repository="Ali-Marandi/Morva",
            candidate_sha="a" * 40,
        )


def test_rebuilt_gate_binding_is_enforced(tmp_path: Path):
    sources = _sources_with_gate(tmp_path)
    payload = json.loads(sources[6].read_text(encoding="utf-8"))
    payload["execution_evidence_fingerprint"] = "0" * 64
    sources[6].write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentIntegrationExecutionReadinessVerificationError,
        match="fingerprint mismatch",
    ):
        verify_execution_readiness(
            execution_evidence=sources[0],
            readiness_gate=sources[1],
            readiness_verification_receipt=sources[2],
            registry_file=sources[3],
            activation_gate=sources[4],
            contract_manifest=sources[5],
            execution_readiness_gate=sources[6],
            repository="Ali-Marandi/Morva",
            candidate_sha="a" * 40,
        )


def test_receipt_write_once(tmp_path: Path):
    sources = _sources_with_gate(tmp_path)
    receipt = verify_execution_readiness(
        execution_evidence=sources[0],
        readiness_gate=sources[1],
        readiness_verification_receipt=sources[2],
        registry_file=sources[3],
        activation_gate=sources[4],
        contract_manifest=sources[5],
        execution_readiness_gate=sources[6],
        repository="Ali-Marandi/Morva",
        candidate_sha="a" * 40,
    )
    output = tmp_path / "verification.json"
    write_receipt(receipt, output)
    with pytest.raises(
        IndependentIntegrationExecutionReadinessVerificationError,
        match="write-once",
    ):
        write_receipt(receipt, output)
