from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from morva.runtime.external_certification_evidence import (
    REQUIRED_ROLES,
    ExternalCertificationEvidenceError,
    ExternalCertificationEvidenceRegistry,
    build_evidence_registry,
    write_registry,
)


REPOSITORY = "Ali-Marandi/Morva"
SHA = "a" * 40

CHECKED_AT = datetime.fromisoformat("2026-09-20T00:00:00+00:00")


def _write_evidence(root: Path, role: str, **overrides) -> Path:
    payload = {
        "evidence_version": 1,
        "role": role,
        "evidence_id": f"E-{role}",
        "repository": REPOSITORY,
        "candidate_sha": SHA,
        "issuer": "external-authority",
        "status": "verified",
        "digest_sha256": "b" * 64,
        "verified_at": "2026-09-19T23:00:00+00:00",
        "expires_at": "2026-10-19T23:00:00+00:00",
    }
    payload.update(overrides)
    path = root / f"{role}.json"
    path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def test_complete_registry_roundtrip(tmp_path: Path):
    paths = tuple(_write_evidence(tmp_path, role) for role in REQUIRED_ROLES)
    items = build_evidence_registry(
        paths,
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )
    registry = ExternalCertificationEvidenceRegistry(
        registry_version=1,
        repository=REPOSITORY,
        candidate_sha=SHA,
        items=items,
        registered_at=datetime.now(timezone.utc),
    )
    assert len(registry.items) == len(REQUIRED_ROLES)
    assert len(registry.fingerprint) == 64


def test_missing_role_is_rejected(tmp_path: Path):
    paths = tuple(
        _write_evidence(tmp_path, role)
        for role in REQUIRED_ROLES[:-1]
    )
    with pytest.raises(ExternalCertificationEvidenceError, match="mismatch"):
        build_evidence_registry(
            paths,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_duplicate_role_is_rejected(tmp_path: Path):
    paths = tuple(
        _write_evidence(tmp_path, role)
        for role in REQUIRED_ROLES[:-1]
    ) + (tmp_path / "legal_approval.json",)
    with pytest.raises(
        ExternalCertificationEvidenceError,
        match="duplicate|invalid",
    ):
        build_evidence_registry(
            paths,
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_expired_evidence_is_rejected(tmp_path: Path):
    path = _write_evidence(
        tmp_path,
        REQUIRED_ROLES[0],
        expires_at="2026-09-18T23:00:00+00:00",
    )
    paths = tuple(_write_evidence(tmp_path, role) for role in REQUIRED_ROLES[1:])
    with pytest.raises(ExternalCertificationEvidenceError, match="expired|mismatch"):
        build_evidence_registry(
            (path, *paths),
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_wrong_sha_is_rejected(tmp_path: Path):
    paths = [
        _write_evidence(tmp_path, role)
        for role in REQUIRED_ROLES
    ]
    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    payload["candidate_sha"] = "c" * 40
    paths[0].write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ExternalCertificationEvidenceError, match="candidate SHA"):
        build_evidence_registry(
            tuple(paths),
            repository=REPOSITORY,
            candidate_sha=SHA,
        )


def test_registry_is_write_once(tmp_path: Path):
    paths = tuple(_write_evidence(tmp_path, role) for role in REQUIRED_ROLES)
    items = build_evidence_registry(
        paths,
        repository=REPOSITORY,
        candidate_sha=SHA,
        checked_at=CHECKED_AT,
    )
    registry = ExternalCertificationEvidenceRegistry(
        registry_version=1,
        repository=REPOSITORY,
        candidate_sha=SHA,
        items=items,
        registered_at=datetime.now(timezone.utc),
    )
    output = tmp_path / "registry.json"
    write_registry(registry, output)
    with pytest.raises(ExternalCertificationEvidenceError, match="write-once"):
        write_registry(registry, output)
