from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.production_release_lineage import build_release_lineage
from morva.runtime.independent_release_lineage_verifier import (
    IndependentLineageVerificationError,
    verify_release_lineage,
    write_receipt,
)
from tests.test_production_release_lineage_m3_70 import _inputs


def test_independent_lineage_roundtrip(tmp_path: Path):
    (
        technical,
        final,
        certification,
        registry,
        policy,
        *_,
    ) = _inputs(tmp_path)
    lineage = build_release_lineage(
        technical_readiness_gate=technical,
        final_readiness_receipt=final,
        production_certification_receipt=certification,
        external_registry=registry,
        policy_receipt=policy,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        verified_at=datetime.fromisoformat(
            "2026-09-20T01:10:00+00:00"
        ),
    )
    manifest = tmp_path / "lineage.json"
    manifest.write_text(
        json.dumps(lineage.to_payload(), sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    receipt = verify_release_lineage(
        technical_readiness_gate=technical,
        final_readiness_receipt=final,
        production_certification_receipt=certification,
        external_registry=registry,
        policy_receipt=policy,
        lineage_manifest=manifest,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
    )
    assert receipt.lineage_fingerprint == lineage.fingerprint


def test_tampered_lineage_is_rejected(tmp_path: Path):
    (
        technical,
        final,
        certification,
        registry,
        policy,
        *_,
    ) = _inputs(tmp_path)
    lineage = build_release_lineage(
        technical_readiness_gate=technical,
        final_readiness_receipt=final,
        production_certification_receipt=certification,
        external_registry=registry,
        policy_receipt=policy,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        verified_at=datetime.fromisoformat(
            "2026-09-20T01:10:00+00:00"
        ),
    )
    manifest = tmp_path / "lineage.json"
    payload = lineage.to_payload()
    payload["candidate_sha"] = "f" * 40
    payload["fingerprint"] = lineage.fingerprint
    manifest.write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        IndependentLineageVerificationError,
        match="fingerprint mismatch",
    ):
        verify_release_lineage(
            technical_readiness_gate=technical,
            final_readiness_receipt=final,
            production_certification_receipt=certification,
            external_registry=registry,
            policy_receipt=policy,
            lineage_manifest=manifest,
            repository="Ali-Marandi/Morva",
            tag="v1.0.1",
            candidate_sha="a" * 40,
        )


def test_receipt_is_write_once(tmp_path: Path):
    (
        technical,
        final,
        certification,
        registry,
        policy,
        *_,
    ) = _inputs(tmp_path)
    lineage = build_release_lineage(
        technical_readiness_gate=technical,
        final_readiness_receipt=final,
        production_certification_receipt=certification,
        external_registry=registry,
        policy_receipt=policy,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        verified_at=datetime.fromisoformat(
            "2026-09-20T01:10:00+00:00"
        ),
    )
    manifest = tmp_path / "lineage.json"
    manifest.write_text(
        json.dumps(lineage.to_payload()) + "\n",
        encoding="utf-8",
    )
    receipt = verify_release_lineage(
        technical_readiness_gate=technical,
        final_readiness_receipt=final,
        production_certification_receipt=certification,
        external_registry=registry,
        policy_receipt=policy,
        lineage_manifest=manifest,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
    )
    output = tmp_path / "verification.json"
    write_receipt(receipt, output)
    with pytest.raises(IndependentLineageVerificationError, match="write-once"):
        write_receipt(receipt, output)
