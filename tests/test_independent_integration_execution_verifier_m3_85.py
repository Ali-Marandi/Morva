from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.independent_integration_execution_verifier import (
    IndependentIntegrationExecutionVerificationError,
    verify_integration_execution,
    write_receipt,
)
from morva.runtime.integration_execution_evidence import (
    load_execution_evidence,
    write_execution_evidence,
)
from tests.test_independent_integration_readiness_verifier_m3_83 import (
    _fixtures as readiness_fixtures,
)
from tests.test_integration_execution_evidence_m3_84 import _receipt as execution_receipt


REPOSITORY = "Ali-Marandi/Morva"
SHA = "a" * 40


def _sources(tmp_path: Path):
    registry, activation, manifest, readiness = readiness_fixtures(tmp_path)
    readiness_receipt_file = tmp_path / "readiness-verification.json"
    from morva.runtime.independent_integration_readiness_verifier import (
        verify_integration_readiness,
        write_receipt as write_readiness_receipt,
    )
    readiness_receipt = verify_integration_readiness(
        registry_file=registry,
        activation_gate=activation,
        contract_manifest=manifest,
        readiness_gate=readiness,
        repository=REPOSITORY,
        candidate_sha=SHA,
    )
    write_readiness_receipt(readiness_receipt, readiness_receipt_file)

    execution_file = tmp_path / "execution.json"
    execution = execution_receipt()
    write_execution_evidence(execution, execution_file)
    return (
        execution_file,
        readiness,
        readiness_receipt_file,
        registry,
        activation,
        manifest,
    )


def test_roundtrip(tmp_path: Path):
    execution, readiness, verification, registry, activation, manifest = _sources(tmp_path)
    result = verify_integration_execution(
        execution_evidence=execution,
        readiness_gate=readiness,
        readiness_verification_receipt=verification,
        registry_file=registry,
        activation_gate=activation,
        contract_manifest=manifest,
        repository=REPOSITORY,
        candidate_sha=SHA,
    )
    assert result.target_environment == "staging"


def test_execution_tamper_is_rejected(tmp_path: Path):
    execution, readiness, verification, registry, activation, manifest = _sources(tmp_path)
    payload = json.loads(execution.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "f" * 40
    execution.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentIntegrationExecutionVerificationError,
        match="execution candidate SHA|fingerprint mismatch",
    ):
        verify_integration_execution(
            execution_evidence=execution,
            readiness_gate=readiness,
            readiness_verification_receipt=verification,
            registry_file=registry,
            activation_gate=activation,
            contract_manifest=manifest,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_readiness_tamper_is_rejected(tmp_path: Path):
    execution, readiness, verification, registry, activation, manifest = _sources(tmp_path)
    payload = json.loads(readiness.read_text(encoding="utf-8"))
    payload["target_environment"] = "pilot"
    readiness.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentIntegrationExecutionVerificationError,
        match="fingerprint mismatch|readiness target",
    ):
        verify_integration_execution(
            execution_evidence=execution,
            readiness_gate=readiness,
            readiness_verification_receipt=verification,
            registry_file=registry,
            activation_gate=activation,
            contract_manifest=manifest,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_execution_before_readiness_is_rejected(tmp_path: Path):
    execution, readiness, verification, registry, activation, manifest = _sources(tmp_path)
    payload = json.loads(execution.read_text(encoding="utf-8"))
    payload["checked_at"] = "2026-09-20T02:30:00+00:00"
    updated = replace(
        load_execution_evidence(execution),
        checked_at=datetime.fromisoformat(payload["checked_at"]),
    )
    payload["evidence_fingerprint"] = updated.evidence_fingerprint
    execution.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentIntegrationExecutionVerificationError,
        match="predates integration readiness|fingerprint mismatch",
    ):
        verify_integration_execution(
            execution_evidence=execution,
            readiness_gate=readiness,
            readiness_verification_receipt=verification,
            registry_file=registry,
            activation_gate=activation,
            contract_manifest=manifest,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_receipt_write_once(tmp_path: Path):
    execution, readiness, verification, registry, activation, manifest = _sources(tmp_path)
    result = verify_integration_execution(
        execution_evidence=execution,
        readiness_gate=readiness,
        readiness_verification_receipt=verification,
        registry_file=registry,
        activation_gate=activation,
        contract_manifest=manifest,
        repository=REPOSITORY,
        candidate_sha=SHA,
    )
    output = tmp_path / "verification.json"
    write_receipt(result, output)
    with pytest.raises(
        IndependentIntegrationExecutionVerificationError,
        match="write-once",
    ):
        write_receipt(result, output)


def test_loaded_execution_evidence_remains_integrity_checked(tmp_path: Path):
    execution = tmp_path / "execution.json"
    receipt = execution_receipt()
    write_execution_evidence(receipt, execution)
    payload = json.loads(execution.read_text(encoding="utf-8"))
    payload["evidence_items"][0]["operator"] = "tampered"
    execution.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        load_execution_evidence(execution)
