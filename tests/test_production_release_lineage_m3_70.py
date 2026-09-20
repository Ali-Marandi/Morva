from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.evidence_freshness_gate import EvidenceFreshnessGate
from morva.runtime.final_production_readiness import FinalProductionReadinessGate
from morva.runtime.final_readiness_verifier import FinalReadinessVerificationReceipt
from morva.runtime.independent_certification_verifier import (
    IndependentCertificationVerificationReceipt,
)
from morva.runtime.production_boundary_policy import (
    ProductionBoundaryPolicyReceipt,
)
from morva.runtime.production_release_lineage import (
    ReleaseLineageError,
    build_release_lineage,
    write_lineage,
)
from morva.runtime.technical_readiness_gate import TechnicalReadinessGate
from tests.test_external_certification_evidence_m3_66 import _write_evidence


REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"
SHA = "a" * 40
ROLES = (
    "legal_approval",
    "finance_approval",
    "security_assessment",
    "operations_approval",
    "authoritative_master_data",
    "official_adapters",
    "reconciliation_evidence",
    "dr_exercise",
    "load_validation",
    "release_certification",
    "publication_evidence",
    "deployment_validation",
)


def _write(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _inputs(tmp_path: Path):
    checked = datetime.fromisoformat("2026-09-20T01:00:00+00:00")
    technical = TechnicalReadinessGate(
        gate_version=1,
        repository=REPOSITORY,
        release_id="Morva Release",
        tag=TAG,
        candidate_sha=SHA,
        bundle_fingerprint="b" * 64,
        promotion_gate_fingerprint="c" * 64,
        promotion_verification_fingerprint="d" * 64,
        policy_fingerprint="e" * 64,
        policy_passed=True,
        source_environment="staging",
        target_environment="production",
        checked_at=checked,
    )
    freshness = EvidenceFreshnessGate(
        gate_version=1,
        repository=REPOSITORY,
        release_id=technical.release_id,
        tag=TAG,
        candidate_sha=SHA,
        bundle_fingerprint=technical.bundle_fingerprint,
        promotion_verification_fingerprint="d" * 64,
        source_environment="staging",
        published_at="2026-09-19T23:00:00+00:00",
        approved_at="2026-09-19T23:30:00+00:00",
        deployed_at="2026-09-19T23:45:00+00:00",
        checked_at=checked,
        max_release_age_hours=24,
        max_approval_age_hours=24,
        max_deployment_age_hours=24,
    )
    final_gate = FinalProductionReadinessGate(
        gate_version=1,
        repository=REPOSITORY,
        release_id=technical.release_id,
        tag=TAG,
        candidate_sha=SHA,
        bundle_fingerprint=technical.bundle_fingerprint,
        technical_readiness_fingerprint=technical.fingerprint,
        freshness_gate_fingerprint=freshness.fingerprint,
        policy_fingerprint=technical.policy_fingerprint,
        source_environment="staging",
        target_environment="production",
        checked_at=datetime.fromisoformat(
            "2026-09-20T01:05:00+00:00"
        ),
    )
    final_receipt = FinalReadinessVerificationReceipt(
        verifier_version=1,
        repository=REPOSITORY,
        release_id=final_gate.release_id,
        tag=TAG,
        candidate_sha=SHA,
        technical_gate_fingerprint=technical.fingerprint,
        freshness_gate_fingerprint=freshness.fingerprint,
        final_gate_fingerprint=final_gate.fingerprint,
        policy_fingerprint=technical.policy_fingerprint,
        source_environment="staging",
        target_environment="production",
        verified_at=datetime.fromisoformat(
            "2026-09-20T01:06:00+00:00"
        ),
    )

    external_root = tmp_path / "external"
    registry_paths = tuple(
        _write_evidence(external_root, role)
        for role in ROLES
    )
    from morva.runtime.external_certification_evidence import (
        ExternalCertificationEvidenceRegistry,
        build_evidence_registry,
    )
    registry_items = build_evidence_registry(
        registry_paths,
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=checked,
    )
    registry = ExternalCertificationEvidenceRegistry(
        registry_version=1,
        repository=REPOSITORY,
        candidate_sha=SHA,
        items=registry_items,
        registered_at=checked,
    )
    certification_receipt = IndependentCertificationVerificationReceipt(
        verifier_version=1,
        repository=REPOSITORY,
        release_id=final_receipt.release_id,
        tag=TAG,
        candidate_sha=SHA,
        final_readiness_fingerprint=final_receipt.fingerprint,
        external_evidence_fingerprint=registry.fingerprint,
        certification_gate_fingerprint="1" * 64,
        verified_roles=ROLES,
        verified_at=datetime.fromisoformat(
            "2026-09-20T01:07:00+00:00"
        ),
    )
    policy = ProductionBoundaryPolicyReceipt(
        policy_version=1,
        repository=REPOSITORY,
        scanned_paths=(
            ".github/workflows/m3-54-release-publication-executor.yml",
            ".github/workflows/m3-55-release-post-publication-integrity.yml",
            ".github/workflows/m3-56-deployment-evidence-gate.yml",
            ".github/workflows/m3-57-independent-deployment-evidence-verifier.yml",
            ".github/workflows/m3-58-deployment-evidence-bundle.yml",
            ".github/workflows/m3-59-production-promotion-gate.yml",
            ".github/workflows/m3-60-independent-production-promotion-verifier.yml",
            ".github/workflows/m3-61-production-boundary-policy.yml",
            ".github/workflows/m3-62-technical-production-readiness.yml",
            ".github/workflows/m3-63-evidence-freshness-gate.yml",
            ".github/workflows/m3-64-final-technical-production-readiness.yml",
            ".github/workflows/m3-65-independent-final-readiness.yml",
            ".github/workflows/m3-66-external-certification-evidence.yml",
            ".github/workflows/m3-67-production-certification-gate.yml",
            ".github/workflows/m3-68-independent-production-certification-verifier.yml",
        ),
        findings=(),
        verified_at=checked,
    )

    technical_file = tmp_path / "technical.json"
    freshness_file = tmp_path / "freshness.json"
    final_file = tmp_path / "final.json"
    certification_file = tmp_path / "certification.json"
    registry_file = tmp_path / "registry.json"
    policy_file = tmp_path / "policy.json"

    _write(
        technical_file,
        {
        "repository": technical.repository,
        "release_id": technical.release_id,
        "tag": technical.tag,
        "candidate_sha": technical.candidate_sha,
        "bundle_fingerprint": technical.bundle_fingerprint,
        "promotion_gate_fingerprint": technical.promotion_gate_fingerprint,
        "promotion_verification_fingerprint": (
            technical.promotion_verification_fingerprint
        ),
        "policy_fingerprint": technical.policy_fingerprint,
        "policy_passed": technical.policy_passed,
        "source_environment": technical.source_environment,
        "target_environment": technical.target_environment,
        "checked_at": technical.checked_at.isoformat(),
        "fingerprint": technical.fingerprint,
    })
    _write(freshness_file, freshness.to_payload())
    _write(final_file, final_receipt.to_payload())
    _write(certification_file, certification_receipt.to_payload())
    _write(registry_file, registry.to_payload())
    _write(policy_file, policy.to_payload())
    return (
        technical_file,
        final_file,
        certification_file,
        registry_file,
        policy_file,
        final_receipt,
        registry,
    )


def test_lineage_roundtrip(tmp_path: Path):
    technical, final, certification, registry, policy, final_obj, registry_obj = _inputs(tmp_path)
    lineage = build_release_lineage(
        technical_readiness_gate=technical,
        final_readiness_receipt=final,
        production_certification_receipt=certification,
        external_registry=registry,
        policy_receipt=policy,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
        verified_at=datetime.fromisoformat("2026-09-20T01:10:00+00:00"),
    )
    assert lineage.bundle_fingerprint == "b" * 64
    assert lineage.final_readiness_fingerprint == final_obj.fingerprint
    assert lineage.external_evidence_fingerprint == registry_obj.fingerprint
    assert lineage.full_policy_fingerprint == json.loads(
        policy.read_text(encoding="utf-8")
    )["fingerprint"]


def test_mismatched_certification_is_rejected(tmp_path: Path):
    technical, final, certification, registry, policy, *_ = _inputs(tmp_path)
    payload = json.loads(certification.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "f" * 40
    certification.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ReleaseLineageError,
        match="certification identity mismatch",
    ):
        build_release_lineage(
            technical_readiness_gate=technical,
            final_readiness_receipt=final,
            production_certification_receipt=certification,
            external_registry=registry,
            policy_receipt=policy,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
            verified_at=datetime.fromisoformat(
                "2026-09-20T01:10:00+00:00"
            ),
        )


def test_write_is_write_once(tmp_path: Path):
    technical, final, certification, registry, policy, *_ = _inputs(tmp_path)
    lineage = build_release_lineage(
        technical_readiness_gate=technical,
        final_readiness_receipt=final,
        production_certification_receipt=certification,
        external_registry=registry,
        policy_receipt=policy,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
        verified_at=datetime.fromisoformat("2026-09-20T01:10:00+00:00"),
    )
    output = tmp_path / "lineage.json"
    write_lineage(lineage, output)
    with pytest.raises(ReleaseLineageError, match="write-once"):
        write_lineage(lineage, output)
