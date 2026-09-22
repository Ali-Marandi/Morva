from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.integration_execution_evidence_bridge import (
    IntegrationExecutionEvidenceBridgeError,
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


def _gate(
    *,
    checked_at: datetime = NOW,
    target_environment: str = "staging",
) -> IntegrationExecutionReadinessGate:
    return IntegrationExecutionReadinessGate(
        gate_version=1,
        repository="Ali-Marandi/Morva",
        candidate_sha=CANDIDATE_SHA,
        target_environment=target_environment,
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


def _write_gate(tmp_path, gate: IntegrationExecutionReadinessGate, **payload_overrides):
    payload = gate.to_payload()
    payload.update(payload_overrides)
    path = tmp_path / "integration-execution-readiness.json"
    path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True),
        encoding="utf-8",
    )
    return path


def _mapping():
    return {
        adapter: f"ADAPTER-{adapter.upper()}-001"
        for adapter in REQUIRED_ADAPTERS
    }


def test_binds_verified_execution_to_all_m4_adapter_contracts(tmp_path):
    gate_path = _write_gate(tmp_path, _gate())
    binding = build_integration_execution_evidence_binding(
        gate_path,
        _registry(),
        repository="Ali-Marandi/Morva",
        candidate_sha=CANDIDATE_SHA,
        bound_by="evidence-operator",
        bound_at=NOW,
        authoritative_evidence_ids=_mapping(),
    )

    assert binding.target_environment == "staging"
    assert binding.execution_id == "EXEC-001"
    assert tuple(row[0] for row in binding.adapter_evidence_bindings) == REQUIRED_ADAPTERS
    assert len(binding.fingerprint) == 64


def test_gate_fingerprint_tampering_is_rejected(tmp_path):
    gate_path = _write_gate(
        tmp_path,
        _gate(),
        fingerprint="f" * 64,
    )

    with pytest.raises(
        IntegrationExecutionEvidenceBridgeError,
        match="fingerprint mismatch",
    ):
        build_integration_execution_evidence_binding(
            gate_path,
            _registry(),
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            bound_by="evidence-operator",
            bound_at=NOW,
            authoritative_evidence_ids=_mapping(),
        )


def test_candidate_sha_mismatch_is_rejected(tmp_path):
    gate_path = _write_gate(tmp_path, _gate())

    with pytest.raises(
        IntegrationExecutionEvidenceBridgeError,
        match="candidate SHA mismatch",
    ):
        build_integration_execution_evidence_binding(
            gate_path,
            _registry(),
            repository="Ali-Marandi/Morva",
            candidate_sha="c" * 40,
            bound_by="evidence-operator",
            bound_at=NOW,
            authoritative_evidence_ids=_mapping(),
        )


def test_missing_adapter_mapping_is_rejected(tmp_path):
    gate_path = _write_gate(tmp_path, _gate())
    mapping = _mapping()
    del mapping["bank"]

    with pytest.raises(
        IntegrationExecutionEvidenceBridgeError,
        match="missing authoritative evidence mapping",
    ):
        build_integration_execution_evidence_binding(
            gate_path,
            _registry(),
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            bound_by="evidence-operator",
            bound_at=NOW,
            authoritative_evidence_ids=mapping,
        )


def test_duplicate_authoritative_evidence_id_is_rejected(tmp_path):
    gate_path = _write_gate(tmp_path, _gate())
    mapping = _mapping()
    mapping["bank"] = mapping["sina"]

    with pytest.raises(
        IntegrationExecutionEvidenceBridgeError,
        match="distinct authoritative evidence id",
    ):
        build_integration_execution_evidence_binding(
            gate_path,
            _registry(),
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            bound_by="evidence-operator",
            bound_at=NOW,
            authoritative_evidence_ids=mapping,
        )


def test_wrong_source_type_is_rejected(tmp_path):
    gate_path = _write_gate(tmp_path, _gate())
    registry = _registry()
    records = list(registry.items)
    records[0] = _item("sina", source_type="master_data")
    wrong_registry = build_registry(tuple(records), registered_at=NOW)

    with pytest.raises(
        IntegrationExecutionEvidenceBridgeError,
        match="adapter_contract source type",
    ):
        build_integration_execution_evidence_binding(
            gate_path,
            wrong_registry,
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            bound_by="evidence-operator",
            bound_at=NOW,
            authoritative_evidence_ids=_mapping(),
        )


def test_expired_authoritative_evidence_is_rejected(tmp_path):
    gate_path = _write_gate(tmp_path, _gate())
    registry = build_registry(
        tuple(_item(adapter, expires_at="2026-09-22T23:59:59+00:00")
              for adapter in REQUIRED_ADAPTERS),
        registered_at=NOW,
    )

    with pytest.raises(
        IntegrationExecutionEvidenceBridgeError,
        match="expired",
    ):
        build_integration_execution_evidence_binding(
            gate_path,
            registry,
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            bound_by="evidence-operator",
            bound_at=NOW,
            authoritative_evidence_ids=_mapping(),
        )


def test_stale_execution_readiness_is_rejected(tmp_path):
    gate_time = NOW - timedelta(hours=25)
    gate_path = _write_gate(
        tmp_path,
        _gate(checked_at=gate_time),
    )

    with pytest.raises(
        IntegrationExecutionEvidenceBridgeError,
        match="stale",
    ):
        build_integration_execution_evidence_binding(
            gate_path,
            _registry(),
            repository="Ali-Marandi/Morva",
            candidate_sha=CANDIDATE_SHA,
            bound_by="evidence-operator",
            bound_at=NOW,
            authoritative_evidence_ids=_mapping(),
        )
