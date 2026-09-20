from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.independent_adapter_evidence_verifier import (
    IndependentAdapterEvidenceVerificationError,
    verify_official_adapter_evidence,
    write_receipt,
)
from morva.runtime.official_adapter_evidence import (
    REQUIRED_ADAPTERS,
    AdapterEvidence,
    build_registry,
    write_registry,
)


REPOSITORY = "Ali-Marandi/Morva"
SHA = "a" * 40
CHECKED_AT = datetime.fromisoformat("2026-09-20T02:30:00+00:00")


def _registry_file(tmp_path: Path) -> Path:
    items = tuple(
        AdapterEvidence(
            evidence_version=1,
            adapter=adapter,
            provider=f"provider-{adapter}",
            repository=REPOSITORY,
            candidate_sha=SHA,
            schema_version="external-v1",
            contract_source=f"external://{adapter}/approved-contract",
            digest_sha256=chr(97 + index) * 64,
            verified_at="2026-09-20T01:00:00+00:00",
        )
        for index, adapter in enumerate(REQUIRED_ADAPTERS)
    )
    registry = build_registry(
        items,
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )
    path = tmp_path / "registry.json"
    write_registry(registry, path)
    return path


def test_roundtrip(tmp_path: Path):
    path = _registry_file(tmp_path)
    receipt = verify_official_adapter_evidence(
        registry_file=path,
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )
    assert receipt.adapters == REQUIRED_ADAPTERS


def test_wrong_sha_is_rejected(tmp_path: Path):
    path = _registry_file(tmp_path)
    with pytest.raises(
        IndependentAdapterEvidenceVerificationError,
        match="candidate SHA",
    ):
        verify_official_adapter_evidence(
            registry_file=path,
            repository=REPOSITORY,
            candidate_sha="f" * 40,
            checked_at=CHECKED_AT,
        )


def test_tampered_registry_is_rejected(tmp_path: Path):
    path = _registry_file(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["items"][0]["provider"] = "tampered"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentAdapterEvidenceVerificationError,
        match="verification failed",
    ):
        verify_official_adapter_evidence(
            registry_file=path,
            repository=REPOSITORY,
            candidate_sha=SHA,
            checked_at=CHECKED_AT,
        )


def test_receipt_write_once(tmp_path: Path):
    path = _registry_file(tmp_path)
    receipt = verify_official_adapter_evidence(
        registry_file=path,
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )
    output = tmp_path / "receipt.json"
    write_receipt(receipt, output)
    with pytest.raises(
        IndependentAdapterEvidenceVerificationError,
        match="write-once",
    ):
        write_receipt(receipt, output)
