from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from morva.runtime.independent_integration_contract_verifier import (
    IndependentIntegrationContractVerificationError,
    verify_integration_contract,
    write_receipt,
)
from morva.runtime.integration_contract_manifest import (
    build_manifest,
    write_manifest,
)

REPOSITORY = "Ali-Marandi/Morva"
SHA = "a" * 40

def test_roundtrip(tmp_path: Path):
    manifest = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at="2026-09-20T04:30:00+00:00",
    )
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    receipt = verify_integration_contract(
        manifest_file=path,
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=datetime.fromisoformat("2026-09-20T05:00:00+00:00"),
    )
    assert receipt.adapters == tuple(
        ("sina", "accounting", "treasury", "bank", "tax", "insurance")
    )


def test_wrong_repository_is_rejected(tmp_path: Path):
    manifest = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at="2026-09-20T04:30:00+00:00",
    )
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    with pytest.raises(
        IndependentIntegrationContractVerificationError,
        match="repository mismatch",
    ):
        verify_integration_contract(
            manifest_file=path,
            repository="Other/Morva",
            candidate_sha=SHA,
        )


def test_port_drift_is_rejected(monkeypatch, tmp_path: Path):
    manifest = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at="2026-09-20T04:30:00+00:00",
    )
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)

    def fake_operations(_port):
        return ("health", "reconcile")

    monkeypatch.setattr(
        "morva.runtime.independent_integration_contract_verifier._public_port_operations",
        fake_operations,
    )
    with pytest.raises(
        IndependentIntegrationContractVerificationError,
        match="operation drift",
    ):
        verify_integration_contract(
            manifest_file=path,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_receipt_write_once(tmp_path: Path):
    manifest = build_manifest(
        repository=REPOSITORY,
        candidate_sha=SHA,
        created_at="2026-09-20T04:30:00+00:00",
    )
    path = tmp_path / "manifest.json"
    write_manifest(manifest, path)
    receipt = verify_integration_contract(
        manifest_file=path,
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=datetime.fromisoformat("2026-09-20T05:00:00+00:00"),
    )
    output = tmp_path / "receipt.json"
    write_receipt(receipt, output)
    with pytest.raises(
        IndependentIntegrationContractVerificationError,
        match="write-once",
    ):
        write_receipt(receipt, output)
