from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from morva.runtime.evidence_freshness_gate import EvidenceFreshnessGate
from morva.runtime.final_production_readiness import (
    FinalProductionReadinessError,
    _load_technical_gate,
    build_final_readiness_gate,
    write_gate,
)
from morva.runtime.technical_readiness_gate import TechnicalReadinessGate


SHA = "a" * 40
BUNDLE = "b" * 64
PROMO = "c" * 64
POLICY = "d" * 64
REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"


def _technical(path: Path) -> None:
    gate = TechnicalReadinessGate(
        gate_version=1,
        repository=REPOSITORY,
        release_id="Morva Release",
        tag=TAG,
        candidate_sha=SHA,
        bundle_fingerprint=BUNDLE,
        promotion_gate_fingerprint="e" * 64,
        promotion_verification_fingerprint=PROMO,
        policy_fingerprint=POLICY,
        policy_passed=True,
        source_environment="staging",
        target_environment="production",
        checked_at=datetime.fromisoformat(
            "2026-09-20T00:00:00+00:00"
        ),
    )
    path.write_text(
        json.dumps(gate.to_payload(), sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )


def _freshness(path: Path) -> None:
    gate = EvidenceFreshnessGate(
        gate_version=1,
        repository=REPOSITORY,
        release_id="Morva Release",
        tag=TAG,
        candidate_sha=SHA,
        bundle_fingerprint=BUNDLE,
        promotion_verification_fingerprint=PROMO,
        published_at="2026-09-19T23:00:00+00:00",
        approved_at="2026-09-19T23:30:00+00:00",
        deployed_at="2026-09-19T23:45:00+00:00",
        checked_at=datetime.fromisoformat(
            "2026-09-20T00:00:00+00:00"
        ),
        max_release_age_hours=24,
        max_approval_age_hours=24,
        max_deployment_age_hours=24,
    )
    path.write_text(
        json.dumps(gate.to_payload(), sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )


def test_final_readiness_roundtrip(tmp_path: Path):
    technical = tmp_path / "technical.json"
    freshness = tmp_path / "freshness.json"
    _technical(technical)
    _freshness(freshness)
    gate = build_final_readiness_gate(
        technical_gate=technical,
        freshness_gate=freshness,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
        checked_at=datetime.fromisoformat(
            "2026-09-20T00:05:00+00:00"
        ),
    )
    assert gate.bundle_fingerprint == BUNDLE
    assert gate.target_environment == "production"


def test_bundle_mismatch_is_rejected(tmp_path: Path):
    technical = tmp_path / "technical.json"
    freshness = tmp_path / "freshness.json"
    _technical(technical)
    _freshness(freshness)
    payload = json.loads(freshness.read_text(encoding="utf-8"))
    payload["bundle_fingerprint"] = "0" * 64
    freshness.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        FinalProductionReadinessError,
        match="fingerprint mismatch",
    ):
        build_final_readiness_gate(
            technical_gate=technical,
            freshness_gate=freshness,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
            checked_at=datetime.fromisoformat(
                "2026-09-20T00:05:00+00:00"
            ),
        )


def test_stale_check_time_order_is_rejected(tmp_path: Path):
    technical = tmp_path / "technical.json"
    freshness = tmp_path / "freshness.json"
    _technical(technical)
    _freshness(freshness)
    with pytest.raises(
        FinalProductionReadinessError,
        match="precedes",
    ):
        build_final_readiness_gate(
            technical_gate=technical,
            freshness_gate=freshness,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
            checked_at=datetime.fromisoformat(
                "2026-09-19T23:00:00+00:00"
            ),
        )


def test_technical_gate_loader_verifies_fingerprint(tmp_path: Path):
    technical = tmp_path / "technical.json"
    _technical(technical)
    payload = json.loads(technical.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "z" * 40
    technical.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        FinalProductionReadinessError,
        match="fingerprint mismatch|structure",
    ):
        _load_technical_gate(technical)


def test_final_gate_is_write_once(tmp_path: Path):
    technical = tmp_path / "technical.json"
    freshness = tmp_path / "freshness.json"
    _technical(technical)
    _freshness(freshness)
    gate = build_final_readiness_gate(
        technical_gate=technical,
        freshness_gate=freshness,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
        checked_at=datetime.fromisoformat(
            "2026-09-20T00:05:00+00:00"
        ),
    )
    output = tmp_path / "final.json"
    write_gate(gate, output)
    with pytest.raises(FinalProductionReadinessError, match="write-once"):
        write_gate(gate, output)
