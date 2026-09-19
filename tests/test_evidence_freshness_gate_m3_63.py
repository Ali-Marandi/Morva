from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from morva.runtime.evidence_freshness_gate import (
    EvidenceFreshnessGateError,
    build_evidence_freshness_gate,
)
from tests.test_production_promotion_verifier_m3_60 import _inputs


REPOSITORY = "Ali-Marandi/Morva"
TAG = "v1.0.1"
SHA = "a" * 40


def _fresh_paths(monkeypatch, tmp_path: Path):
    return _inputs(monkeypatch, tmp_path)


def test_freshness_gate_roundtrip(monkeypatch, tmp_path: Path):
    bundle, metadata, promotion_gate, auth, attestation = _fresh_paths(
        monkeypatch,
        tmp_path,
    )
    release_receipt = tmp_path / "release-receipt.json"
    # The helper's receipt is not exposed as a standalone path, so derive it
    # from the evidence bundle for the fixture.
    import tarfile
    with tarfile.open(bundle, mode="r:gz") as archive:
        member = archive.extractfile("release_post_publication_receipt.json")
        assert member is not None
        release_receipt.write_bytes(member.read())

    checked_at = datetime.fromisoformat(
        "2026-09-20T00:00:00+00:00"
    )
    gate = build_evidence_freshness_gate(
        bundle_archive=bundle,
        bundle_metadata=metadata,
        promotion_gate=promotion_gate,
        authorization=auth,
        deployment_attestation=attestation,
        release_receipt=release_receipt,
        repository=REPOSITORY,
        tag=TAG,
        candidate_sha=SHA,
        checked_at=checked_at,
        max_release_age_hours=24 * 30,
        max_approval_age_hours=24,
        max_deployment_age_hours=24,
    )
    assert gate.candidate_sha == SHA


def test_stale_approval_is_rejected(monkeypatch, tmp_path: Path):
    bundle, metadata, promotion_gate, auth, attestation = _fresh_paths(
        monkeypatch,
        tmp_path,
    )
    release_receipt = tmp_path / "release-receipt.json"
    import tarfile
    with tarfile.open(bundle, mode="r:gz") as archive:
        member = archive.extractfile("release_post_publication_receipt.json")
        assert member is not None
        release_receipt.write_bytes(member.read())
    with pytest.raises(EvidenceFreshnessGateError, match="approval is stale"):
        build_evidence_freshness_gate(
            bundle_archive=bundle,
            bundle_metadata=metadata,
            promotion_gate=promotion_gate,
            authorization=auth,
            deployment_attestation=attestation,
            release_receipt=release_receipt,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
            checked_at=datetime.fromisoformat("2026-09-20T12:00:00+00:00"),
            max_release_age_hours=24 * 30,
            max_approval_age_hours=1,
            max_deployment_age_hours=24,
        )


def test_future_timestamp_is_rejected(monkeypatch, tmp_path: Path):
    bundle, metadata, promotion_gate, auth, attestation = _fresh_paths(
        monkeypatch,
        tmp_path,
    )
    release_receipt = tmp_path / "release-receipt.json"
    import tarfile
    with tarfile.open(bundle, mode="r:gz") as archive:
        member = archive.extractfile("release_post_publication_receipt.json")
        assert member is not None
        release_receipt.write_bytes(member.read())
    with pytest.raises(
        EvidenceFreshnessGateError,
        match="future",
    ):
        build_evidence_freshness_gate(
            bundle_archive=bundle,
            bundle_metadata=metadata,
            promotion_gate=promotion_gate,
            authorization=auth,
            deployment_attestation=attestation,
            release_receipt=release_receipt,
            repository=REPOSITORY,
            tag=TAG,
            candidate_sha=SHA,
            checked_at=datetime.fromisoformat("2026-09-19T22:00:00+00:00"),
            max_release_age_hours=24 * 30,
            max_approval_age_hours=24,
            max_deployment_age_hours=24,
        )
