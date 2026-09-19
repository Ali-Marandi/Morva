from __future__ import annotations

import json
from pathlib import Path

import pytest

from morva.runtime.deployment_evidence_bundle import _load_metadata
from morva.runtime.production_promotion_gate import (
    build_production_promotion_gate,
)
from morva.runtime.production_promotion_verifier import (
    ProductionPromotionGateError,
    verify_production_promotion,
    write_verification_receipt,
)
from tests.test_production_promotion_gate_m3_59 import (
    _authorization,
    _promotion_inputs,
)

REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"
SHA = "a" * 40


def _inputs(monkeypatch, tmp_path: Path):
    bundle, metadata, attestation = _promotion_inputs(monkeypatch, tmp_path)
    bundle_object = _load_metadata(metadata)
    authorization_file = tmp_path / "authorization.json"
    authorization_file.write_text(
        json.dumps(_authorization(bundle_object.bundle_fingerprint)),
        encoding="utf-8",
    )
    promotion_gate = tmp_path / "promotion-gate.json"
    gate = build_production_promotion_gate(
        bundle_archive=bundle,
        bundle_metadata=metadata,
        authorization_file=authorization_file,
        deployment_attestation=attestation,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    promotion_gate.write_text(
        json.dumps(gate.to_payload(), sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return bundle, metadata, promotion_gate, authorization_file, attestation


def test_independent_promotion_verifier_roundtrip(monkeypatch, tmp_path: Path):
    bundle, metadata, promotion_gate, auth, attestation = _inputs(
        monkeypatch,
        tmp_path,
    )
    result = verify_production_promotion(
        bundle_archive=bundle,
        bundle_metadata=metadata,
        promotion_gate=promotion_gate,
        authorization=auth,
        deployment_attestation=attestation,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    assert result.source_environment == "staging"
    assert result.target_environment == "production"


def test_verifier_rejects_gate_tampering(monkeypatch, tmp_path: Path):
    bundle, metadata, promotion_gate, auth, attestation = _inputs(
        monkeypatch,
        tmp_path,
    )
    payload = json.loads(promotion_gate.read_text(encoding="utf-8"))
    payload["deployment_id"] = "tampered"
    promotion_gate.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ProductionPromotionGateError,
        match="fingerprint mismatch",
    ):
        verify_production_promotion(
            bundle_archive=bundle,
            bundle_metadata=metadata,
            promotion_gate=promotion_gate,
            authorization=auth,
            deployment_attestation=attestation,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_verifier_rejects_authorization_mismatch(
    monkeypatch,
    tmp_path: Path,
):
    bundle, metadata, promotion_gate, auth, attestation = _inputs(
        monkeypatch,
        tmp_path,
    )
    payload = json.loads(auth.read_text(encoding="utf-8"))
    payload["authorization_id"] = "PROMO-OTHER"
    auth.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ProductionPromotionGateError,
        match="authorization id mismatch",
    ):
        verify_production_promotion(
            bundle_archive=bundle,
            bundle_metadata=metadata,
            promotion_gate=promotion_gate,
            authorization=auth,
            deployment_attestation=attestation,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_verifier_rejects_external_attestation_mismatch(
    monkeypatch,
    tmp_path: Path,
):
    bundle, metadata, promotion_gate, auth, attestation = _inputs(
        monkeypatch,
        tmp_path,
    )
    payload = json.loads(attestation.read_text(encoding="utf-8"))
    payload["healthcheck_sha256"] = "0" * 64
    attestation.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        ProductionPromotionGateError,
        match="does not match bundle attestation",
    ):
        verify_production_promotion(
            bundle_archive=bundle,
            bundle_metadata=metadata,
            promotion_gate=promotion_gate,
            authorization=auth,
            deployment_attestation=attestation,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
        )


def test_verification_receipt_is_write_once(monkeypatch, tmp_path: Path):
    bundle, metadata, promotion_gate, auth, attestation = _inputs(
        monkeypatch,
        tmp_path,
    )
    result = verify_production_promotion(
        bundle_archive=bundle,
        bundle_metadata=metadata,
        promotion_gate=promotion_gate,
        authorization=auth,
        deployment_attestation=attestation,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
    )
    output = tmp_path / "verification.json"
    write_verification_receipt(result, output)
    with pytest.raises(
        ProductionPromotionGateError,
        match="write-once",
    ):
        write_verification_receipt(result, output)
