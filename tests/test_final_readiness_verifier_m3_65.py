from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.evidence_freshness_gate import EvidenceFreshnessGate
from morva.runtime.final_production_readiness import (
    TechnicalReadinessGate,
    build_final_readiness_gate,
)
from morva.runtime.final_readiness_verifier import (
    FinalReadinessVerificationError,
    verify_final_readiness,
    write_receipt,
)


SHA = "a" * 40
BUNDLE = "b" * 64
TECH_PROMO = "c" * 64
POLICY = "d" * 64
REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"


def _inputs(tmp_path: Path):
    technical = TechnicalReadinessGate(
        gate_version=1,
        repository=REPOSITORY,
        release_id="Morva Release",
        tag=TAG,
        candidate_sha=SHA,
        bundle_fingerprint=BUNDLE,
        promotion_gate_fingerprint="e" * 64,
        promotion_verification_fingerprint=TECH_PROMO,
        policy_fingerprint=POLICY,
        policy_passed=True,
        source_environment="staging",
        target_environment="production",
        checked_at=datetime.fromisoformat("2026-09-20T00:00:00+00:00"),
    )
    freshness = EvidenceFreshnessGate(
        gate_version=1,
        repository=REPOSITORY,
        release_id="Morva Release",
        tag=TAG,
        candidate_sha=SHA,
        bundle_fingerprint=BUNDLE,
        promotion_verification_fingerprint=TECH_PROMO,
        published_at="2026-09-19T23:00:00+00:00",
        approved_at="2026-09-19T23:30:00+00:00",
        deployed_at="2026-09-19T23:45:00+00:00",
        checked_at=datetime.fromisoformat("2026-09-20T00:00:00+00:00"),
        max_release_age_hours=24,
        max_approval_age_hours=24,
        max_deployment_age_hours=24,
    )
    technical_file = tmp_path / "technical.json"
    freshness_file = tmp_path / "freshness.json"
    technical_file.write_text(
        json.dumps(technical.to_payload(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    freshness_file.write_text(
        json.dumps(freshness.to_payload(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    final = build_final_readiness_gate(
        technical_gate=technical_file,
        freshness_gate=freshness_file,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
        checked_at=datetime.fromisoformat("2026-09-20T00:05:00+00:00"),
    )
    final_file = tmp_path / "final.json"
    final_file.write_text(
        json.dumps(final.to_payload(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return technical_file, freshness_file, final_file


def test_independent_verifier_roundtrip(tmp_path: Path):
    technical, freshness, final = _inputs(tmp_path)
    receipt = verify_final_readiness(
        technical_gate=technical,
        freshness_gate=freshness,
        final_gate=final,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    assert receipt.target_environment == "production"


def test_final_gate_tamper_is_rejected(tmp_path: Path):
    technical, freshness, final = _inputs(tmp_path)
    payload = json.loads(final.read_text(encoding="utf-8"))
    payload["policy_fingerprint"] = "0" * 64
    final.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        FinalReadinessVerificationError,
        match="fingerprint mismatch",
    ):
        verify_final_readiness(
            technical_gate=technical,
            freshness_gate=freshness,
            final_gate=final,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_final_gate_cross_binding_is_rejected(tmp_path: Path):
    technical, freshness, final = _inputs(tmp_path)
    payload = json.loads(final.read_text(encoding="utf-8"))
    payload["bundle_fingerprint"] = "0" * 64
    from morva.runtime.final_production_readiness import (
        FinalProductionReadinessGate,
    )

    tampered = FinalProductionReadinessGate(
        gate_version=payload["gate_version"],
        repository=payload["repository"],
        release_id=payload["release_id"],
        tag=payload["tag"],
        candidate_sha=payload["candidate_sha"],
        bundle_fingerprint=payload["bundle_fingerprint"],
        technical_readiness_fingerprint=payload[
            "technical_readiness_fingerprint"
        ],
        freshness_gate_fingerprint=payload["freshness_gate_fingerprint"],
        policy_fingerprint=payload["policy_fingerprint"],
        source_environment=payload["source_environment"],
        target_environment=payload["target_environment"],
        checked_at=datetime.fromisoformat(payload["checked_at"]),
    )
    payload["fingerprint"] = tampered.fingerprint
    final.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        FinalReadinessVerificationError,
        match="bundle fingerprint mismatch",
    ):
        verify_final_readiness(
            technical_gate=technical,
            freshness_gate=freshness,
            final_gate=final,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_receipt_is_write_once(tmp_path: Path):
    technical, freshness, final = _inputs(tmp_path)
    receipt = verify_final_readiness(
        technical_gate=technical,
        freshness_gate=freshness,
        final_gate=final,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    output = tmp_path / "verification.json"
    write_receipt(receipt, output)
    with pytest.raises(FinalReadinessVerificationError, match="write-once"):
        write_receipt(receipt, output)
