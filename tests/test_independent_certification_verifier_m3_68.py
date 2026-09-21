from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from morva.runtime.external_certification_evidence import (
    REQUIRED_ROLES,
    ExternalCertificationEvidence,
    ExternalCertificationEvidenceRegistry,
)
from morva.runtime.final_readiness_verifier import verify_final_readiness
from morva.runtime.independent_certification_verifier import (
    IndependentCertificationVerificationError,
    verify_production_certification,
    write_receipt,
)
from morva.runtime.production_certification_gate import (
    ProductionCertificationGate,
)
from tests.test_production_certification_gate_m3_67 import (
    _readiness_files,
    _registry,
)


def _inputs(tmp_path: Path):
    technical, freshness, final = _readiness_files(tmp_path)
    registry = _registry(tmp_path)
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(
        json.dumps(registry.to_payload()) + "\n",
        encoding="utf-8",
    )
    readiness = verify_final_readiness(
        technical_gate=technical,
        freshness_gate=freshness,
        final_gate=final,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
    )
    certification = ProductionCertificationGate(
        gate_version=1,
        repository="Ali-Marandi/Morva",
        release_id=readiness.release_id,
        tag="v1.0.1",
        candidate_sha="a" * 40,
        final_readiness_fingerprint=readiness.fingerprint,
        external_evidence_fingerprint=registry.fingerprint,
        required_roles=REQUIRED_ROLES,
        verified_roles=REQUIRED_ROLES,
        certified_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    certification_file = tmp_path / "certification.json"
    certification_file.write_text(
        json.dumps(certification.to_payload()) + "\n",
        encoding="utf-8",
    )
    return technical, freshness, final, registry_file, certification_file


def test_roundtrip(tmp_path: Path):
    technical, freshness, final, registry, certification = _inputs(tmp_path)
    result = verify_production_certification(
        final_technical_gate=technical,
        final_freshness_gate=freshness,
        final_gate=final,
        external_registry=registry,
        certification_gate=certification,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
    )
    assert result.verified_roles == REQUIRED_ROLES


def test_gate_tamper_is_rejected(tmp_path: Path):
    technical, freshness, final, registry, certification = _inputs(tmp_path)
    payload = json.loads(certification.read_text(encoding="utf-8"))
    payload["candidate_sha"] = "f" * 40
    certification.write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        IndependentCertificationVerificationError,
        match="fingerprint mismatch",
    ):
        verify_production_certification(
            final_technical_gate=technical,
            final_freshness_gate=freshness,
            final_gate=final,
            external_registry=registry,
            certification_gate=certification,
            repository="Ali-Marandi/Morva",
            tag="v1.0.1",
            candidate_sha="a" * 40,
        )


def test_registry_binding_is_rejected(tmp_path: Path):
    technical, freshness, final, registry, certification = _inputs(tmp_path)
    payload = json.loads(certification.read_text(encoding="utf-8"))
    payload["external_evidence_fingerprint"] = "0" * 64
    gate = ProductionCertificationGate(
        gate_version=payload["gate_version"],
        repository=payload["repository"],
        release_id=payload["release_id"],
        tag=payload["tag"],
        candidate_sha=payload["candidate_sha"],
        final_readiness_fingerprint=payload["final_readiness_fingerprint"],
        external_evidence_fingerprint=payload["external_evidence_fingerprint"],
        required_roles=tuple(payload["required_roles"]),
        verified_roles=tuple(payload["verified_roles"]),
        certified_at=datetime.fromisoformat(payload["certified_at"]),
    )
    payload["fingerprint"] = gate.fingerprint
    certification.write_text(
        json.dumps(payload) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        IndependentCertificationVerificationError,
        match="external evidence fingerprint mismatch",
    ):
        verify_production_certification(
            final_technical_gate=technical,
            final_freshness_gate=freshness,
            final_gate=final,
            external_registry=registry,
            certification_gate=certification,
            repository="Ali-Marandi/Morva",
            tag="v1.0.1",
            candidate_sha="a" * 40,
        )


def test_expired_evidence_is_rejected(tmp_path: Path):
    technical, freshness, final, registry, certification = _inputs(tmp_path)
    payload = json.loads(registry.read_text(encoding="utf-8"))
    payload["items"][0]["expires_at"] = "2026-09-20T00:00:00+00:00"
    items = tuple(
        ExternalCertificationEvidence(
            evidence_version=int(item["evidence_version"]),
            role=item["role"],
            evidence_id=item["evidence_id"],
            repository=item["repository"],
            candidate_sha=item["candidate_sha"],
            issuer=item["issuer"],
            status=item["status"],
            digest_sha256=item["digest_sha256"],
            verified_at=item["verified_at"],
            expires_at=item.get("expires_at"),
        )
        for item in payload["items"]
    )
    tampered = ExternalCertificationEvidenceRegistry(
        registry_version=int(payload["registry_version"]),
        repository=payload["repository"],
        candidate_sha=payload["candidate_sha"],
        items=items,
        registered_at=datetime.fromisoformat(payload["registered_at"]),
    )
    registry.write_text(
        json.dumps(tampered.to_payload()) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        IndependentCertificationVerificationError,
        match="external evidence fingerprint mismatch|expired",
    ):
        verify_production_certification(
            final_technical_gate=technical,
            final_freshness_gate=freshness,
            final_gate=final,
            external_registry=registry,
            certification_gate=certification,
            repository="Ali-Marandi/Morva",
            tag="v1.0.1",
            candidate_sha="a" * 40,
        )


def test_receipt_is_write_once(tmp_path: Path):
    technical, freshness, final, registry, certification = _inputs(tmp_path)
    result = verify_production_certification(
        final_technical_gate=technical,
        final_freshness_gate=freshness,
        final_gate=final,
        external_registry=registry,
        certification_gate=certification,
        repository="Ali-Marandi/Morva",
        tag="v1.0.1",
        candidate_sha="a" * 40,
    )
    output = tmp_path / "verification.json"
    write_receipt(result, output)
    with pytest.raises(
        IndependentCertificationVerificationError,
        match="write-once",
    ):
        write_receipt(result, output)
