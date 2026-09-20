from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from morva.runtime.evidence_freshness_gate import EvidenceFreshnessGate
from morva.runtime.final_production_readiness import (
    FinalProductionReadinessGate,
)
from morva.runtime.final_readiness_verifier import (
    FinalReadinessVerificationReceipt,
)
from morva.runtime.production_certification_gate import (
    ProductionCertificationGate,
)
from morva.runtime.independent_certification_verifier import (
    IndependentCertificationVerificationReceipt,
)
from morva.runtime.production_boundary_policy import (
    PolicyFinding,
    ProductionBoundaryPolicyReceipt,
)
from morva.runtime.technical_readiness_gate import TechnicalReadinessGate
from morva.runtime.production_release_lineage import (
    ReleaseLineageError,
    build_release_lineage,
    write_lineage,
)


REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"
SHA = "a" * 40


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
        release_id="Morva Release",
        tag=TAG,
        candidate_sha=SHA,
        bundle_fingerprint="b" * 64,
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
    final = FinalProductionReadinessGate(
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
        release_id=final.release_id,
        tag=TAG,
        candidate_sha=SHA,
        technical_gate_fingerprint=technical.fingerprint,
        freshness_gate_fingerprint=freshness.fingerprint,
        final_gate_fingerprint=final.fingerprint,
        policy_fingerprint=technical.policy_fingerprint,
        source_environment="staging",
        target_environment="production",
        verified_at=datetime.fromisoformat(
            "2026-09-20T01:06:00+00:00"
        ),
    )
    registry_items = tuple(
        # The lineage layer only reloads the registry fingerprint;
        # actual registry semantics are covered by M3.66.
        object() for _ in range(0)
    )
    certification_receipt = IndependentCertificationVerificationReceipt(
        verifier_version=1,
        repository=REPOSITORY,
        release_id=final.release_id,
        tag=TAG,
        candidate_sha=SHA,
        final_readiness_fingerprint=final_receipt.fingerprint,
        external_evidence_fingerprint="f" * 64,
        certification_gate_fingerprint="1" * 64,
        verified_roles=(
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
        ),
        verified_at=datetime.fromisoformat(
            "2026-09-20T01:07:00+00:00"
        ),
    )
    policy = ProductionBoundaryPolicyReceipt(
        policy_version=1,
        repository=REPOSITORY,
        scanned_paths=(
            ".github/workflows/m3-54-release-publication-executor.yml",
        ),
        findings=(),
        verified_at=checked,
    )
    technical_file = tmp_path / "technical.json"
    final_file = tmp_path / "final.json"
    freshness_file = tmp_path / "freshness.json"
    certification_file = tmp_path / "certification.json"
    registry_file = tmp_path / "registry.json"
    policy_file = tmp_path / "policy.json"
    technical_file.write_text(
        json.dumps(technical.to_payload(), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write(final_file, final_receipt.to_payload())
    _write(freshness_file, freshness.to_payload())
    _write(certification_file, certification_receipt.to_payload())
    _write(
        registry_file,
        {
            "registry_version": 1,
            "repository": REPOSITORY,
            "candidate_sha": SHA,
            "items": [],
            "registered_at": checked.isoformat(),
            "fingerprint": "f" * 64,
        },
    )
    _write(policy_file, policy.to_payload())
    return (
        technical_file,
        final_file,
        freshness_file,
        certification_file,
        registry_file,
        policy_file,
        technical,
        final_receipt,
        certification_receipt,
        policy,
    )


def test_lineage_roundtrip(tmp_path: Path):
    (
        technical,
        final,
        _freshness,
        certification,
        registry,
        policy,
        technical_obj,
        final_obj,
        cert_obj,
        policy_obj,
    ) = _inputs(tmp_path)
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["items"] = [
        {
            "evidence_version": 1,
            "role": role,
            "evidence_id": role,
            "repository": REPOSITORY,
            "candidate_sha": SHA,
            "issuer": "authority",
            "status": "verified",
            "digest_sha256": "2" * 64,
            "verified_at": "2026-09-20T00:00:00+00:00",
            "expires_at": None,
        }
        for role in cert_obj.verified_roles
    ]
    from morva.runtime.external_certification_evidence import (
        ExternalCertificationEvidence,
        ExternalCertificationEvidenceRegistry,
    )

    items = tuple(
        ExternalCertificationEvidence(**item)
        for item in payload["items"]
    )
    registry_obj = ExternalCertificationEvidenceRegistry(
        registry_version=1,
        repository=REPOSITORY,
        candidate_sha=SHA,
        items=items,
        registered_at=datetime.fromisoformat(
            "2026-09-20T00:00:00+00:00"
        ),
    )
    _write(registry, registry_obj.to_payload())
    _write(policy, policy_obj.to_payload())
    lineage = build_release_lineage(
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
    assert lineage.bundle_fingerprint == technical_obj.bundle_fingerprint
    assert lineage.final_readiness_fingerprint == final_obj.fingerprint
    assert lineage.external_evidence_fingerprint == registry_obj.fingerprint


def test_mismatched_certification_is_rejected(tmp_path: Path):
    technical, final, _freshness, certification, registry, policy, *_ = _inputs(tmp_path)
    payload = json.loads(certification.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "f" * 40
    certification.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ReleaseLineageError,
        match="certification identity mismatch|candidate SHA mismatch",
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
            verified_at=datetime.now(timezone.utc),
        )


def test_write_is_write_once(tmp_path: Path):
    (
        technical,
        final,
        _freshness,
        certification,
        registry,
        policy,
        *_,
    ) = _inputs(tmp_path)
    payload = json.loads(registry.read_text(encoding="utf-8"))
    from morva.runtime.external_certification_evidence import (
        ExternalCertificationEvidence,
        ExternalCertificationEvidenceRegistry,
    )

    items = tuple(
        ExternalCertificationEvidence(
            evidence_version=1,
            role=role,
            evidence_id=role,
            repository=REPOSITORY,
            candidate_sha=SHA,
            issuer="authority",
            status="verified",
            digest_sha256="2" * 64,
            verified_at="2026-09-20T00:00:00+00:00",
            expires_at=None,
        )
        for role in (
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
    )
    registry_obj = ExternalCertificationEvidenceRegistry(
        registry_version=1,
        repository=REPOSITORY,
        candidate_sha=SHA,
        items=items,
        registered_at=datetime.fromisoformat(
            "2026-09-20T00:00:00+00:00"
        ),
    )
    _write(registry, registry_obj.to_payload())
    lineage = build_release_lineage(
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
    output = tmp_path / "lineage.json"
    write_lineage(lineage, output)
    with pytest.raises(ReleaseLineageError, match="write-once"):
        write_lineage(lineage, output)
