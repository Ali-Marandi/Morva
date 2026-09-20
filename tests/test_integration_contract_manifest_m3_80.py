from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from morva.runtime.integration_contract_manifest import (
    ADAPTER_OPERATIONS,
    IntegrationContractManifestError,
    build_manifest,
    load_manifest,
    write_manifest,
)


REPOSITORY = "Ali-Marandi/Morva"
SHA = "a" * 40
CREATED = "2026-09-20T04:00:00+00:00"


def test_manifest_is_deterministic():
    first = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at=CREATED,
    )
    second = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at=CREATED,
    )
    assert first.fingerprint == second.fingerprint
    assert first.adapters == tuple(ADAPTER_OPERATIONS)


def test_roundtrip(tmp_path: Path):
    manifest = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at=CREATED,
    )
    output = tmp_path / "manifest.json"
    write_manifest(manifest, output)
    loaded = load_manifest(output)
    assert loaded == manifest


def test_tampered_manifest_is_rejected(tmp_path: Path):
    manifest = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at=CREATED,
    )
    output = tmp_path / "manifest.json"
    write_manifest(manifest, output)
    text = output.read_text(encoding="utf-8")
    output.write_text(text.replace("publish_order", "publish_order_v2"), encoding="utf-8")
    with pytest.raises(
        IntegrationContractManifestError,
        match="operation|fingerprint",
    ):
        load_manifest(output)


def test_wrong_candidate_is_rejected():
    with pytest.raises(IntegrationContractManifestError, match="candidate_sha"):
        build_manifest(
            repository=REPOSITORY,
            candidate_sha="f" * 39,
            created_at=CREATED,
        )


def test_noncanonical_adapters_are_rejected():
    manifest = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at=CREATED,
    )
    with pytest.raises(IntegrationContractManifestError, match="canonical"):
        replace(manifest, adapters=("bank", "sina"))


def test_write_once(tmp_path: Path):
    manifest = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at=CREATED,
    )
    output = tmp_path / "manifest.json"
    write_manifest(manifest, output)
    with pytest.raises(IntegrationContractManifestError, match="write-once"):
        write_manifest(manifest, output)
