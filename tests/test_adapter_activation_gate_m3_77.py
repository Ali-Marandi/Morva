from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.adapter_activation_gate import (
    AdapterActivationAuthorization,
    AdapterActivationGateError,
    build_activation_gate,
    write_gate,
)
from morva.runtime.official_adapter_evidence import (
    REQUIRED_ADAPTERS,
    AdapterEvidence,
    build_registry,
    write_registry,
)

REPOSITORY = "Ali-Marandi/Morva"
SHA = "a" * 40
CHECKED_AT = datetime.fromisoformat("2026-09-20T03:00:00+00:00")


def _registry_file(tmp_path: Path):
    items = tuple(
        AdapterEvidence(
            evidence_version=1,
            adapter=adapter,
            provider=f"provider-{adapter}",
            repository=REPOSITORY,
            candidate_sha=SHA,
            schema_version="external-v1",
            contract_source=f"external://{adapter}/approved-contract",
            digest_sha256=chr(97 + i) * 64,
            verified_at="2026-09-20T01:00:00+00:00",
        )
        for i, adapter in enumerate(REQUIRED_ADAPTERS)
    )
    registry = build_registry(
        items,
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )
    path = tmp_path / "registry.json"
    write_registry(registry, path)
    return path, registry.fingerprint


def _auth(fingerprint: str):
    return AdapterActivationAuthorization(
        authorization_id="AUTH-001",
        registry_fingerprint=fingerprint,
        approved=True,
        approved_at="2026-09-20T02:00:00+00:00",
        approver="external-operator",
        target_environment="staging",
    )


def test_roundtrip(tmp_path: Path):
    registry, fingerprint = _registry_file(tmp_path)
    gate = build_activation_gate(
        registry_file=registry,
        authorization=_auth(fingerprint),
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )
    assert gate.adapters == REQUIRED_ADAPTERS


def test_unapproved_is_rejected(tmp_path: Path):
    registry, fingerprint = _registry_file(tmp_path)
    auth = replace(_auth(fingerprint), approved=False)
    with pytest.raises(AdapterActivationGateError, match="not approved"):
        build_activation_gate(
            registry_file=registry,
            authorization=auth,
            repository=REPOSITORY,
            candidate_sha=SHA,
            checked_at=CHECKED_AT,
        )


def test_wrong_binding_is_rejected(tmp_path: Path):
    registry, _ = _registry_file(tmp_path)
    with pytest.raises(AdapterActivationGateError, match="does not match"):
        build_activation_gate(
            registry_file=registry,
            authorization=_auth("0" * 64),
            repository=REPOSITORY,
            candidate_sha=SHA,
            checked_at=CHECKED_AT,
        )


def test_future_authorization_is_rejected(tmp_path: Path):
    registry, fingerprint = _registry_file(tmp_path)
    auth = replace(
        _auth(fingerprint),
        approved_at="2026-09-20T04:00:00+00:00",
    )
    with pytest.raises(AdapterActivationGateError, match="future"):
        build_activation_gate(
            registry_file=registry,
            authorization=auth,
            repository=REPOSITORY,
            candidate_sha=SHA,
            checked_at=CHECKED_AT,
        )


def test_registry_tamper_is_rejected(tmp_path: Path):
    registry, fingerprint = _registry_file(tmp_path)
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["items"][0]["provider"] = "tampered"
    registry.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(AdapterActivationGateError, match="independently verified"):
        build_activation_gate(
            registry_file=registry,
            authorization=_auth(fingerprint),
            repository=REPOSITORY,
            candidate_sha=SHA,
            checked_at=CHECKED_AT,
        )


def test_write_once(tmp_path: Path):
    registry, fingerprint = _registry_file(tmp_path)
    gate = build_activation_gate(
        registry_file=registry,
        authorization=_auth(fingerprint),
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )
    output = tmp_path / "activation-gate.json"
    write_gate(gate, output)
    with pytest.raises(AdapterActivationGateError, match="write-once"):
        write_gate(gate, output)
