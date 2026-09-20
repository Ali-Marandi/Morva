from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.integration_execution_readiness_gate import (
    IntegrationExecutionReadinessGateError,
    build_integration_execution_readiness_gate,
    write_gate,
)
from tests.test_independent_integration_execution_verifier_m3_85 import _sources


def _build(tmp_path: Path, checked_at: str, max_age: int = 24):
    execution, readiness, verification, registry, activation, manifest = _sources(tmp_path)
    return build_integration_execution_readiness_gate(
        execution_evidence=execution,
        readiness_gate=readiness,
        readiness_verification_receipt=verification,
        registry_file=registry,
        activation_gate=activation,
        contract_manifest=manifest,
        repository="Ali-Marandi/Morva",
        candidate_sha="a" * 40,
        checked_at=datetime.fromisoformat(checked_at),
        max_execution_age_hours=max_age,
    )


def test_roundtrip_and_binding(tmp_path: Path):
    gate = _build(tmp_path, "2026-09-20T11:00:00+00:00")
    assert gate.target_environment == "staging"
    assert gate.adapters
    assert len(gate.fingerprint) == 64


def test_stale_execution_is_rejected(tmp_path: Path):
    with pytest.raises(IntegrationExecutionReadinessGateError, match="stale"):
        _build(tmp_path, "2026-09-20T11:00:00+00:00", 1)


def test_production_execution_is_rejected(tmp_path: Path):
    execution, readiness, verification, registry, activation, manifest = _sources(tmp_path)
    payload = json.loads(execution.read_text(encoding="utf-8"))
    payload["target_environment"] = "production"
    execution.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IntegrationExecutionReadinessGateError,
        match="M3.84/M3.85|environment",
    ):
        build_integration_execution_readiness_gate(
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


def test_gate_is_write_once(tmp_path: Path):
    gate = _build(tmp_path, "2026-09-20T11:00:00+00:00")
    path = tmp_path / "gate.json"
    write_gate(gate, path)
    with pytest.raises(IntegrationExecutionReadinessGateError, match="write-once"):
        write_gate(gate, path)
