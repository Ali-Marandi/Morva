from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from morva.runtime.external_certification_evidence import (
    REQUIRED_ROLES,
    ExternalCertificationEvidenceRegistry,
    build_evidence_registry,
)
from morva.runtime.production_certification_gate import (
    ProductionCertificationGateError,
    build_production_certification_gate,
    load_registry,
    write_gate,
)
from morva.runtime.evidence_freshness_gate import EvidenceFreshnessGate
from morva.runtime.technical_readiness_gate import TechnicalReadinessGate
from tests.test_external_certification_evidence_m3_66 import _write_evidence


def _readiness_files(tmp_path: Path):
    sha = "a" * 40
    repo = "Ali-Marandi/Morva"
    tag = "v1.0.1"
    technical_file = tmp_path / "technical.json"
    freshness_file = tmp_path / "freshness.json"
    final_file = tmp_path / "final.json"

    technical = TechnicalReadinessGate(
        gate_version=1,
        repository=repo,
        release_id="Morva Release",
        tag=tag,
        candidate_sha=sha,
        bundle_fingerprint="b" * 64,
        promotion_gate_fingerprint="c" * 64,
        promotion_verification_fingerprint="d" * 64,
        policy_fingerprint="e" * 64,
        policy_passed=True,
        source_environment="staging",
        target_environment="production",
        checked_at=datetime.fromisoformat("2026-09-20T00:00:00+00:00"),
    )
    freshness = EvidenceFreshnessGate(
        gate_version=1,
        repository=repo,
        release_id="Morva Release",
        tag=tag,
        candidate_sha=sha,
        bundle_fingerprint="b" * 64,
        promotion_verification_fingerprint="d" * 64,
        source_environment="staging",
        published_at="2026-09-19T23:00:00+00:00",
        approved_at="2026-09-19T23:30:00+00:00",
        deployed_at="2026-09-19T23:45:00+00:00",
        checked_at=datetime.fromisoformat("2026-09-20T00:00:00+00:00"),
        max_release_age_hours=24,
        max_approval_age_hours=24,
        max_deployment_age_hours=24,
    )
    technical_file.write_text(
        json.dumps(technical.to_payload()) + "\n",
        encoding="utf-8",
    )
    freshness_file.write_text(
        json.dumps(freshness.to_payload()) + "\n",
        encoding="utf-8",
    )

    from morva.runtime.final_production_readiness import (
        build_final_readiness_gate,
    )

    final_gate = build_final_readiness_gate(
        technical_gate=technical_file,
        freshness_gate=freshness_file,
        repository=repo,
        tag=tag,
        candidate_sha=sha,
        checked_at=datetime.fromisoformat("2026-09-20T00:05:00+00:00"),
    )
    final_file.write_text(
        json.dumps(final_gate.to_payload()) + "\n",
        encoding="utf-8",
    )
    return technical_file, freshness_file, final_file


def _registry(tmp_path: Path):
    paths = tuple(_write_evidence(tmp_path, role) for role in REQUIRED_ROLES)
    items = build_evidence_registry(
        paths,
        repository="Ali-Marandi/Morva",
        candidate_sha="a" * 40,
        checked_at=datetime.fromisoformat("2026-09-20T00:00:00+00:00"),
    )
    return ExternalCertificationEvidenceRegistry(
        registry_version=1,
        repository="Ali-Marandi/Morva",
        candidate_sha="a" * 40,
        items=items,
        registered_at=datetime.fromisoformat("2026-09-20T00:00:00+00:00"),
    )


def test_certification_gate_requires_all_external_roles(tmp_path: Path):
    technical, freshness, final = _readiness_files(tmp_path)
    registry = _registry(tmp_path)
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(
        json.dumps(registry.to_payload()) + "\n",
        encoding="utf-8",
    )
    loaded = load_registry(registry_file)
    gate = build_production_certification_gate(
        final_technical_gate=technical,
        final_freshness_gate=freshness,
        final_gate=final,
        external_registry=loaded,
        final_readiness_repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        certified_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    assert gate.verified_roles == REQUIRED_ROLES
    assert len(gate.fingerprint) == 64


def test_registry_tamper_is_rejected(tmp_path: Path):
    registry = _registry(tmp_path)
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(
        json.dumps(registry.to_payload()) + "\n",
        encoding="utf-8",
    )
    payload = json.loads(registry_file.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "c" * 40
    registry_file.write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ProductionCertificationGateError,
        match="fingerprint mismatch",
    ):
        load_registry(registry_file)


def test_gate_is_write_once(tmp_path: Path):
    technical, freshness, final = _readiness_files(tmp_path)
    registry = _registry(tmp_path)
    gate = build_production_certification_gate(
        final_technical_gate=technical,
        final_freshness_gate=freshness,
        final_gate=final,
        external_registry=registry,
        final_readiness_repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
        certified_at=datetime.fromisoformat("2026-09-20T00:10:00+00:00"),
    )
    output = tmp_path / "certification.json"
    write_gate(gate, output)
    with pytest.raises(ProductionCertificationGateError, match="write-once"):
        write_gate(gate, output)


def test_candidate_sha_mismatch_is_rejected(tmp_path: Path):
    technical, freshness, final = _readiness_files(tmp_path)
    registry = _registry(tmp_path)
    with pytest.raises(
        ProductionCertificationGateError,
        match="candidate SHA",
    ):
        build_production_certification_gate(
            final_technical_gate=technical,
            final_freshness_gate=freshness,
            final_gate=final,
            external_registry=registry,
            final_readiness_repository="Ali-Marandi/Morva",
            tag="v1.0.1",
            candidate_sha="f" * 40,
            certified_at=datetime.fromisoformat("2026-09-20T00:10:00+00:00"),
        )
