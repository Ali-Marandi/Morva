from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.external_certification_evidence import REQUIRED_ROLES
from morva.runtime.independent_handoff_verifier import (
    IndependentHandoffVerificationError,
    verify_handoff,
    write_receipt,
)
from morva.runtime.production_readiness_convergence import ProductionReadinessConvergence
from morva.runtime.production_readiness_handoff import build_handoff


def _fixtures(tmp_path: Path):
    source_root = tmp_path / "sources"
    source_root.mkdir()
    convergence_file = source_root / "convergence.json"
    convergence_file.write_text(
        json.dumps(
            {
                "convergence_version": 1,
                "repository": "Ali-Marandi/Morva",
                "release_id": "Morva Release",
                "tag": "v1.0.1",
                "candidate_sha": "a" * 40,
                "lineage_fingerprint": "b" * 64,
                "lineage_verification_fingerprint": "c" * 64,
                "full_policy_fingerprint": "d" * 64,
                "certification_verification_fingerprint": "e" * 64,
                "verified_roles": list(REQUIRED_ROLES),
                "source_environment": "staging",
                "target_environment": "production",
                "converged_at": "2026-09-20T01:30:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    payload = json.loads(convergence_file.read_text(encoding="utf-8"))
    payload["fingerprint"] = ProductionReadinessConvergence(
        convergence_version=payload["convergence_version"],
        repository=payload["repository"],
        release_id=payload["release_id"],
        tag=payload["tag"],
        candidate_sha=payload["candidate_sha"],
        lineage_fingerprint=payload["lineage_fingerprint"],
        lineage_verification_fingerprint=payload["lineage_verification_fingerprint"],
        full_policy_fingerprint=payload["full_policy_fingerprint"],
        certification_verification_fingerprint=payload["certification_verification_fingerprint"],
        verified_roles=tuple(payload["verified_roles"]),
        source_environment=payload["source_environment"],
        target_environment=payload["target_environment"],
        converged_at=datetime.fromisoformat(payload["converged_at"]),
    ).fingerprint
    convergence_file.write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )
    handoff = build_handoff(
        root=source_root,
        source_paths=("convergence.json",),
        repository="Ali-Marandi/Morva",
        release_id="Morva Release",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        convergence_fingerprint=payload["fingerprint"],
        created_at=datetime.fromisoformat("2026-09-20T01:31:00+00:00"),
    )
    handoff_file = tmp_path / "handoff.json"
    from morva.runtime.production_readiness_handoff import write_handoff

    write_handoff(handoff, handoff_file)
    return convergence_file, handoff_file


def test_roundtrip(tmp_path: Path):
    convergence, handoff = _fixtures(tmp_path)
    receipt = verify_handoff(
        convergence_file=convergence,
        handoff_file=handoff,
        source_root=tmp_path / "sources",
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
    )
    assert receipt.convergence_fingerprint


def test_handoff_fingerprint_mismatch_is_rejected(tmp_path: Path):
    convergence, handoff = _fixtures(tmp_path)
    payload = json.loads(handoff.read_text(encoding="utf-8"))
    payload["convergence_fingerprint"] = "0" * 64
    handoff.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        IndependentHandoffVerificationError,
        match="handoff fingerprint mismatch",
    ):
        verify_handoff(
            convergence_file=convergence,
            handoff_file=handoff,
            source_root=tmp_path / "sources",
            repository="Ali-Marandi/Morva",
            tag="v1.0.1",
            candidate_sha="a" * 40,
        )


def test_convergence_source_tamper_is_rejected(tmp_path: Path):
    convergence, handoff = _fixtures(tmp_path)
    convergence.write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(
        IndependentHandoffVerificationError,
        match="convergence structure|fingerprint|source",
    ):
        verify_handoff(
            convergence_file=convergence,
            handoff_file=handoff,
            source_root=tmp_path / "sources",
            repository="Ali-Marandi/Morva",
            tag="v1.0.1",
            candidate_sha="a" * 40,
        )


def test_receipt_is_write_once(tmp_path: Path):
    convergence, handoff = _fixtures(tmp_path)
    receipt = verify_handoff(
        convergence_file=convergence,
        handoff_file=handoff,
        source_root=tmp_path / "sources",
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
    )
    output = tmp_path / "verification.json"
    write_receipt(receipt, output)
    with pytest.raises(IndependentHandoffVerificationError, match="write-once"):
        write_receipt(receipt, output)
