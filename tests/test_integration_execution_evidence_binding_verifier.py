from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.integration_execution_evidence_binding_verifier import (
    IntegrationExecutionEvidenceBindingVerificationError,
    verify_integration_execution_evidence_binding,
)
from morva.runtime.integration_execution_evidence_bridge import (
    build_integration_execution_evidence_binding,
)
from morva.runtime.integration_execution_readiness_gate import (
    IntegrationExecutionReadinessGate,
)
from morva.runtime.official_adapter_evidence import REQUIRED_ADAPTERS

NOW = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
CANDIDATE_SHA = "b" * 40
DIGEST = "a" * 64


def _item(adapter: str, **overrides) -> AuthoritativeEvidenceItem:
    payload = {
        "intake_version": 1,
        "evidence_id": f"ADAPTER-{adapter.upper()}-001",
        "source_type": "adapter_contract",
        "source_uri": f"https://authority.example/contracts/{adapter}",
        "source_sha256": DIGEST,
        "issuer": "adapter-authority",
        "population_scope": "enterprise",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "approver",
        "approved_at": "2026-09-20T10:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def _registry(**overrides):
    items = tuple(_item(adapter, **overrides) for adapter in REQUIRED_ADAPTERS)
    return build_registry(items, registered_at=NOW)


def _gate(*, checked_at: datetime = NOW) -> IntegrationExecutionReadinessGate:
    return IntegrationExecutionReadinessGate(
        gate_version=1,
        repository="Ali-Marandi/Morva",
        candidate_sha=CANDIDATE_SHA,
        target_environment="staging",
        adapters=REQUIRED_ADAPTERS,
        execution_id="EXEC-001",
        execution_evidence_fingerprint="1" * 64,
        execution_verification_fingerprint="2" * 64,
        readiness_gate_fingerprint="3" * 64,
        readiness_verification_fingerprint="4" * 64,
        latest_execution_finished_at=(
            checked_at - timedelta(hours=1)
        ).isoformat(),
        checked_at=checked_at,
        max_execution_age_hours=24,
    )


def _write_json(tmp_path, name: str, payload: dict[str, object]):
    path = tmp_path / name
    path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _write_gate(tmp_path, gate: IntegrationExecutionReadinessGate, **overrides):
    payload = gate.to_payload()
    payload.update(overrides)
    return _write_json(tmp_path, "integration-execution-readiness.json", payload)


def _mapping() -> dict[str, str]:
    return {
        adapter: f"ADAPTER-{adapter.upper()}-001"
        for adapter in REQUIRED_ADAPTERS
    }


def _write_binding(tmp_path, mapping=None):
    mapping = mapping or _mapping()
    gate = _gate()
    gate_path = _write_gate(tmp_path, gate)
    binding = build_integration_execution_evidence_binding(
        gate_path,
        _registry(),
        repository="Ali-Marandi/Morva",
        candidate_sha=CANDIDATE_SHA,
        bound_by="evidence-operator",
        bound_at=NOW,
        authoritative_evidence_ids=mapping,
    )
    return (
        gate_path,
        _write_json(tmp_path, "integration-execution-binding.json", binding.to_payload()),
        binding,
    )


def test_independently_reconstructs_binding(tmp_path):
    gate_path, binding_path, binding = _write_binding(tmp_path)

    verification = verify_integration_execution_evidence_binding(
        binding_path,
        gate_path,
        _registry(),
        repository="Ali-Marandi/Morva",
        candidate_sha=CANDIDATE_SHA,
        authoritative_evidence_ids=_mapping(),
        verified_at=NOW,
    )

    assert verification.binding == binding
    assert len(verification.fingerprint) == 64


def test_binding_fingerprint_tampering_is_rejected(tmp_path):
    gate_path, binding_path, _ = _write_binding(tmp_path)
    payload = json.loads(binding_path.read_text(encoding="utf-8"))
    payload["fingerprint"] = "f" * 64
    binding_path = _write_json(tmp_path, "tampered-binding.json", payload)

    with pytest.raises(
        IntegrationExecutionEvidenceBindingVerificationError,
        match="fingerprint mismatch",
    ):
        verify_integration_execution_evidence_binding(
            binding_path,
            gate_path,
            _registry(),
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            authoritative_evidence_ids=_mapping(),
            verified_at=NOW,
        )


def test_registry_fingerprint_mismatch_is_rejected(tmp_path):
    gate_path, binding_path, _ = _write_binding(tmp_path)
    changed_items = tuple(
        replace(_item(adapter), source_sha256="c" * 64)
        for adapter in REQUIRED_ADAPTERS
    )
    changed_registry = build_registry(changed_items, registered_at=NOW)

    with pytest.raises(
        IntegrationExecutionEvidenceBindingVerificationError,
        match="registry fingerprint mismatch",
    ):
        verify_integration_execution_evidence_binding(
            binding_path,
            gate_path,
            changed_registry,
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            authoritative_evidence_ids=_mapping(),
            verified_at=NOW,
        )


def test_candidate_sha_mismatch_is_rejected(tmp_path):
    gate_path, binding_path, _ = _write_binding(tmp_path)

    with pytest.raises(
        IntegrationExecutionEvidenceBindingVerificationError,
        match="candidate SHA mismatch",
    ):
        verify_integration_execution_evidence_binding(
            binding_path,
            gate_path,
            _registry(),
            repository="Ali-Marandi/Morva",
            candidate_sha="c" * 40,
            authoritative_evidence_ids=_mapping(),
            verified_at=NOW,
        )


def test_authoritative_mapping_mismatch_is_rejected(tmp_path):
    gate_path, binding_path, _ = _write_binding(tmp_path)
    mapping = _mapping()
    mapping["bank"] = "ADAPTER-SINA-001"

    with pytest.raises(
        IntegrationExecutionEvidenceBindingVerificationError,
        match="distinct authoritative evidence id",
    ):
        verify_integration_execution_evidence_binding(
            binding_path,
            gate_path,
            _registry(),
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            authoritative_evidence_ids=mapping,
            verified_at=NOW,
        )


def test_gate_tampering_is_rejected_during_reconstruction(tmp_path):
    _, binding_path, _ = _write_binding(tmp_path)
    tampered_gate_path = _write_gate(
        tmp_path,
        _gate(),
        execution_verification_fingerprint="9" * 64,
    )

    with pytest.raises(
        IntegrationExecutionEvidenceBindingVerificationError,
        match="structure is invalid|fingerprint mismatch",
    ):
        verify_integration_execution_evidence_binding(
            binding_path,
            tampered_gate_path,
            _registry(),
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            authoritative_evidence_ids=_mapping(),
            verified_at=NOW,
        )
