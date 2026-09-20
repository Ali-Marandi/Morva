from __future__ import annotations

import json
from pathlib import Path

import pytest

from morva.runtime.production_promotion_gate import (
    ProductionPromotionGateError,
    build_production_promotion_gate,
    load_authorization,
    write_gate,
)
from tests.test_deployment_evidence_bundle_m3_58 import _inputs
from morva.runtime.deployment_evidence_bundle import (
    build_deployment_evidence_bundle,
)

REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"
SHA = "a" * 40


def _promotion_inputs(monkeypatch, tmp_path: Path):
    release, gate, attestation, verification = _inputs(
        monkeypatch,
        tmp_path / "source",
    )
    bundle_archive = tmp_path / "bundle.tar.gz"
    bundle_metadata = tmp_path / "bundle.json"
    build_deployment_evidence_bundle(
        release_receipt_file=release,
        deployment_gate_file=gate,
        attestation_file=attestation,
        deployment_verification_receipt_file=verification,
        output_archive=bundle_archive,
        metadata_file=bundle_metadata,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    return bundle_archive, bundle_metadata, attestation


def _authorization(bundle_fingerprint: str, **overrides) -> dict[str, object]:
    payload = {
        "authorization_version": 1,
        "authorization_id": "PROMO-001",
        "bundle_fingerprint": bundle_fingerprint,
        "source_environment": "staging",
        "target_environment": "production",
        "approved": True,
        "approved_at": "2026-09-19T23:30:00+00:00",
        "approver": "release-approver",
        "scope": "github_production_promotion",
    }
    payload.update(overrides)
    return payload


def test_promotion_gate_roundtrip(monkeypatch, tmp_path: Path):
    bundle, metadata, attestation = _promotion_inputs(monkeypatch, tmp_path)
    from morva.runtime.deployment_evidence_bundle import _load_metadata

    bundle_object = _load_metadata(metadata)
    authorization = tmp_path / "authorization.json"
    authorization.write_text(
        json.dumps(_authorization(bundle_object.bundle_fingerprint))
        + "\n",
        encoding="utf-8",
    )
    gate = build_production_promotion_gate(
        bundle_archive=bundle,
        bundle_metadata=metadata,
        authorization_file=authorization,
        deployment_attestation=attestation,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    assert gate.source_environment == "staging"
    assert gate.target_environment == "production"
    assert gate.deployment_operator == "release-operator"


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("bundle_fingerprint", "0" * 64, "not bound"),
        ("source_environment", "pilot", "environment"),
        ("target_environment", "staging", "target_environment"),
        ("approver", "release-operator", "distinct"),
    ],
)
def test_promotion_rejects_bad_authorization(
    monkeypatch,
    tmp_path: Path,
    field: str,
    value: str,
    match: str,
):
    bundle, metadata, attestation = _promotion_inputs(monkeypatch, tmp_path)
    from morva.runtime.deployment_evidence_bundle import _load_metadata

    bundle_object = _load_metadata(metadata)
    payload = _authorization(bundle_object.bundle_fingerprint)
    payload[field] = value
    authorization = tmp_path / "authorization.json"
    authorization.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )
    with pytest.raises(ProductionPromotionGateError, match=match):
        build_production_promotion_gate(
            bundle_archive=bundle,
            bundle_metadata=metadata,
            authorization_file=authorization,
            deployment_attestation=attestation,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_string_boolean_is_rejected(tmp_path: Path):
    authorization = tmp_path / "authorization.json"
    authorization.write_text(
        json.dumps(
            _authorization(
                "0" * 64,
                approved="false",
            )
        ),
        encoding="utf-8",
    )
    with pytest.raises(ProductionPromotionGateError, match="Boolean"):
        load_authorization(authorization)


def test_promotion_gate_is_write_once(monkeypatch, tmp_path: Path):
    bundle, metadata, attestation = _promotion_inputs(monkeypatch, tmp_path)
    from morva.runtime.deployment_evidence_bundle import _load_metadata

    bundle_object = _load_metadata(metadata)
    authorization = tmp_path / "authorization.json"
    authorization.write_text(
        json.dumps(_authorization(bundle_object.bundle_fingerprint))
        + "\n",
        encoding="utf-8",
    )
    gate = build_production_promotion_gate(
        bundle_archive=bundle,
        bundle_metadata=metadata,
        authorization_file=authorization,
        deployment_attestation=attestation,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    output = tmp_path / "promotion-gate.json"
    write_gate(gate, output)
    with pytest.raises(ProductionPromotionGateError, match="write-once"):
        write_gate(gate, output)

def test_promotion_rejects_external_attestation_mismatch(
    monkeypatch,
    tmp_path: Path,
):
    bundle, metadata, attestation = _promotion_inputs(monkeypatch, tmp_path)
    from morva.runtime.deployment_evidence_bundle import _load_metadata

    bundle_object = _load_metadata(metadata)
    payload = _authorization(bundle_object.bundle_fingerprint)
    authorization = tmp_path / "authorization.json"
    authorization.write_text(json.dumps(payload), encoding="utf-8")

    external = json.loads(attestation.read_text(encoding="utf-8"))
    external["deployment_id"] = "different-deployment"
    attestation.write_text(
        json.dumps(external, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ProductionPromotionGateError,
        match="does not match bundle attestation",
    ):
        build_production_promotion_gate(
            bundle_archive=bundle,
            bundle_metadata=metadata,
            authorization_file=authorization,
            deployment_attestation=attestation,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )
