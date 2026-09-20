from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.production_readiness_convergence import (
    ProductionReadinessConvergenceError,
    build_convergence,
    write_convergence,
)
from morva.runtime.production_release_lineage import build_release_lineage
from morva.runtime.independent_release_lineage_verifier import (
    verify_release_lineage,
    write_receipt as write_lineage_receipt,
)
from tests.test_independent_release_lineage_verifier_m3_71 import _inputs


def _sources(tmp_path: Path):
    technical, final, certification, registry, policy, *_ = _inputs(tmp_path)
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
    lineage_file = tmp_path / "lineage.json"
    lineage_file.write_text(
        json.dumps(lineage.to_payload()) + "\n",
        encoding="utf-8",
    )
    verification = verify_release_lineage(
        technical_readiness_gate=technical,
        final_readiness_receipt=final,
        production_certification_receipt=certification,
        external_registry=registry,
        policy_receipt=policy,
        lineage_manifest=lineage_file,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
    )
    verification_file = tmp_path / "lineage-verification.json"
    write_lineage_receipt(verification, verification_file)
    return technical, final, certification, registry, policy, lineage_file, verification_file


def _build(tmp_path: Path):
    return build_convergence(
        technical_readiness_gate=tmp_path / "technical.json",
        final_readiness_receipt=tmp_path / "final.json",
        production_certification_receipt=tmp_path / "certification.json",
        external_registry=tmp_path / "registry.json",
        policy_receipt=tmp_path / "policy.json",
        lineage_manifest=tmp_path / "lineage.json",
        lineage_verification_receipt=tmp_path / "lineage-verification.json",
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        converged_at=datetime.fromisoformat(
            "2026-09-20T01:15:00+00:00"
        ),
    )


def test_roundtrip(tmp_path: Path):
    _sources(tmp_path)
    convergence = _build(tmp_path)
    assert convergence.verified_roles
    assert convergence.target_environment == "production"


def test_tampered_lineage_receipt_is_rejected(tmp_path: Path):
    _sources(tmp_path)
    path = tmp_path / "lineage-verification.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "f" * 40
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        ProductionReadinessConvergenceError,
        match="receipt fingerprint mismatch|candidate SHA|identity",
    ):
        _build(tmp_path)


def test_policy_fingerprint_mismatch_is_rejected(tmp_path: Path):
    _sources(tmp_path)
    path = tmp_path / "lineage.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["full_policy_fingerprint"] = "0" * 64
    from morva.runtime.production_release_lineage import ProductionReleaseLineage

    tampered = ProductionReleaseLineage(
        **{
            **payload,
            "verified_at": datetime.fromisoformat(payload["verified_at"]),
            "full_policy_fingerprint": "0" * 64,
        }
    )
    payload["fingerprint"] = tampered.fingerprint
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(
        ProductionReadinessConvergenceError,
        match="full-policy fingerprint",
    ):
        _build(tmp_path)


def test_noncanonical_roles_are_rejected(tmp_path: Path):
    _sources(tmp_path)
    path = tmp_path / "registry.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["items"] = payload["items"][:-1]
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(ProductionReadinessConvergenceError):
        _build(tmp_path)


def test_write_once(tmp_path: Path):
    _sources(tmp_path)
    convergence = _build(tmp_path)
    output = tmp_path / "convergence.json"
    write_convergence(convergence, output)
    with pytest.raises(ProductionReadinessConvergenceError, match="write-once"):
        write_convergence(convergence, output)
