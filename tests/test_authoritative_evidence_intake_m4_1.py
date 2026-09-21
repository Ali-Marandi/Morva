from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceIntakeError,
    AuthoritativeEvidenceItem,
    build_registry,
    write_registry,
)


SHA = "a" * 64
NOW = datetime.fromisoformat("2026-09-22T10:00:00+00:00")


def _item(**overrides) -> AuthoritativeEvidenceItem:
    payload = {
        "intake_version": 1,
        "evidence_id": "E-001",
        "source_type": "legal_rule",
        "source_uri": "https://authority.example/evidence/E-001",
        "source_sha256": SHA,
        "issuer": "authority",
        "population_scope": "teachers",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "reviewer-1",
        "approved_at": "2026-09-20T10:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def test_item_has_deterministic_fingerprint():
    first = _item()
    second = _item()
    assert first.fingerprint == second.fingerprint
    assert len(first.fingerprint) == 64


def test_pending_evidence_is_not_activation_ready():
    item = _item(status="pending", approved_by=None, approved_at=None)
    registry = build_registry((item,), registered_at=NOW)
    assert not registry.is_activation_ready(NOW)


def test_expired_accepted_evidence_is_not_activation_ready():
    item = _item(expires_at="2026-09-21T23:59:59+00:00")
    registry = build_registry((item,), registered_at=NOW)
    assert not registry.is_activation_ready(NOW)


def test_accepted_nonexpired_evidence_is_activation_ready():
    item = _item()
    registry = build_registry((item,), registered_at=NOW)
    assert registry.is_activation_ready(NOW)


def test_future_effective_evidence_is_not_activation_ready():
    item = _item(
        effective_from="2026-09-23T00:00:00+00:00",
        effective_to="2027-01-01T00:00:00+00:00",
    )
    registry = build_registry((item,), registered_at=NOW)
    assert not registry.is_activation_ready(NOW)


def test_future_approval_is_not_activation_ready():
    item = _item(approved_at="2026-09-23T10:00:00+00:00")
    registry = build_registry((item,), registered_at=NOW)
    assert not registry.is_activation_ready(NOW)


def test_duplicate_evidence_ids_are_rejected():
    first = _item(evidence_id="E-001")
    second = _item(evidence_id="E-001")
    with pytest.raises(AuthoritativeEvidenceIntakeError, match="duplicate"):
        build_registry((first, second), registered_at=NOW)


def test_accepted_evidence_requires_approval_actor_and_time():
    with pytest.raises(
        AuthoritativeEvidenceIntakeError,
        match="approved_by",
    ):
        _item(approved_by=None)


def test_invalid_effective_window_is_rejected():
    with pytest.raises(
        AuthoritativeEvidenceIntakeError,
        match="effective_to",
    ):
        _item(
            effective_from="2026-10-01T00:00:00+00:00",
            effective_to="2026-09-01T00:00:00+00:00",
        )


def test_write_once_registry(tmp_path: Path):
    registry = build_registry((_item(),), registered_at=NOW)
    path = tmp_path / "registry.json"
    write_registry(registry, path)
    with pytest.raises(AuthoritativeEvidenceIntakeError, match="write-once"):
        write_registry(registry, path)


def test_payload_roundtrip_is_json_safe():
    payload = _item().to_payload()
    encoded = json.dumps(payload, sort_keys=True)
    assert "fingerprint" in encoded
