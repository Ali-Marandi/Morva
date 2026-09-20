from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from morva.runtime.production_release_lineage import (
    ReleaseLineageError,
    build_release_lineage,
    write_lineage,
)


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _inputs(tmp_path: Path):
    final = tmp_path / "final.json"
    certification = tmp_path / "certification.json"
    registry = tmp_path / "registry.json"
    policy = tmp_path / "policy.json"
    _write(
        final,
        {
            "repository": "Ali-Marandi/Morva",
            "release_id": "Morva Release",
            "tag": "v1.0.1",
            "candidate_sha": "a" * 40,
            "bundle_fingerprint": "b" * 64,
            "freshness_gate_fingerprint": "c" * 64,
            "source_environment": "staging",
            "target_environment": "production",
            "fingerprint": "d" * 64,
        },
    )
    _write(
        certification,
        {
            "repository": "Ali-Marandi/Morva",
            "tag": "v1.0.1",
            "candidate_sha": "a" * 40,
            "release_id": "Morva Release",
            "external_evidence_fingerprint": "e" * 64,
            "fingerprint": "f" * 64,
        },
    )
    _write(
        registry,
        {
            "repository": "Ali-Marandi/Morva",
            "candidate_sha": "a" * 40,
        },
    )
    _write(
        policy,
        {
            "repository": "Ali-Marandi/Morva",
            "passed": True,
            "fingerprint": "1" * 64,
        },
    )
    return final, certification, registry, policy


def test_lineage_roundtrip(tmp_path: Path):
    final, certification, registry, policy = _inputs(tmp_path)
    lineage = build_release_lineage(
        final_readiness_receipt=final,
        production_certification_receipt=certification,
        external_registry=registry,
        policy_receipt=policy,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        verified_at=datetime.fromisoformat(
            "2026-09-20T01:00:00+00:00"
        ),
    )
    assert lineage.bundle_fingerprint == "b" * 64
    assert len(lineage.fingerprint) == 64


def test_mismatched_certification_is_rejected(tmp_path: Path):
    final, certification, registry, policy = _inputs(tmp_path)
    payload = json.loads(certification.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "f" * 40
    certification.write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ReleaseLineageError,
        match="certification candidate SHA mismatch",
    ):
        build_release_lineage(
            final_readiness_receipt=final,
            production_certification_receipt=certification,
            external_registry=registry,
            policy_receipt=policy,
            repository="Ali-Marandi/Morva",
            tag="v1.0.1",
            candidate_sha="a" * 40,
            verified_at=datetime.now(timezone.utc),
        )


def test_policy_failure_is_rejected(tmp_path: Path):
    final, certification, registry, policy = _inputs(tmp_path)
    payload = json.loads(policy.read_text(encoding="utf-8"))
    payload["passed"] = False
    policy.write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ReleaseLineageError, match="policy"):
        build_release_lineage(
            final_readiness_receipt=final,
            production_certification_receipt=certification,
            external_registry=registry,
            policy_receipt=policy,
            repository="Ali-Marandi/Morva",
            tag="v1.0.1",
            candidate_sha="a" * 40,
            verified_at=datetime.now(timezone.utc),
        )


def test_write_is_write_once(tmp_path: Path):
    final, certification, registry, policy = _inputs(tmp_path)
    lineage = build_release_lineage(
        final_readiness_receipt=final,
        production_certification_receipt=certification,
        external_registry=registry,
        policy_receipt=policy,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        verified_at=datetime.now(timezone.utc),
    )
    output = tmp_path / "lineage.json"
    write_lineage(lineage, output)
    with pytest.raises(ReleaseLineageError, match="write-once"):
        write_lineage(lineage, output)
