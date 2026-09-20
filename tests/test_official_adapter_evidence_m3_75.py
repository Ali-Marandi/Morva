from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.official_adapter_evidence import (
    REQUIRED_ADAPTERS,
    AdapterEvidence,
    OfficialAdapterEvidenceError,
    assert_activation_ready,
    build_registry,
    load_registry,
    write_registry,
)

REPOSITORY = "Ali-Marandi/Morva"
SHA = "a" * 40
CHECKED_AT = datetime.fromisoformat("2026-09-20T02:00:00+00:00")


def _items():
    return tuple(
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


def _registry():
    return build_registry(
        _items(),
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )


def test_roundtrip_and_activation_readiness():
    registry = _registry()
    assert registry.fingerprint
    assert_activation_ready(
        registry,
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )


def test_missing_adapter_is_rejected():
    with pytest.raises(
        OfficialAdapterEvidenceError,
        match="canonical order|complete",
    ):
        build_registry(
            _items()[:-1],
            repository=REPOSITORY,
            candidate_sha=SHA,
            checked_at=CHECKED_AT,
        )


def test_wrong_sha_is_rejected():
    item = replace(_items()[0], candidate_sha="f" * 40)
    with pytest.raises(OfficialAdapterEvidenceError, match="candidate SHA"):
        build_registry(
            (item,) + _items()[1:],
            repository=REPOSITORY,
            candidate_sha=SHA,
            checked_at=CHECKED_AT,
        )


def test_expired_evidence_is_rejected():
    item = replace(
        _items()[0],
        expires_at="2026-09-20T01:59:59+00:00",
    )
    with pytest.raises(OfficialAdapterEvidenceError, match="expired"):
        build_registry(
            (item,) + _items()[1:],
            repository=REPOSITORY,
            candidate_sha=SHA,
            checked_at=CHECKED_AT,
        )


def test_future_evidence_is_rejected():
    item = replace(
        _items()[0],
        verified_at="2026-09-20T03:00:00+00:00",
    )
    with pytest.raises(OfficialAdapterEvidenceError, match="future"):
        build_registry(
            (item,) + _items()[1:],
            repository=REPOSITORY,
            candidate_sha=SHA,
            checked_at=CHECKED_AT,
        )


def test_tampered_manifest_is_rejected(tmp_path: Path):
    registry = _registry()
    path = tmp_path / "registry.json"
    write_registry(registry, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["items"][0]["provider"] = "tampered"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        OfficialAdapterEvidenceError,
        match="fingerprint mismatch",
    ):
        load_registry(path)


def test_write_once(tmp_path: Path):
    registry = _registry()
    path = tmp_path / "registry.json"
    write_registry(registry, path)
    with pytest.raises(OfficialAdapterEvidenceError, match="write-once"):
        write_registry(registry, path)
