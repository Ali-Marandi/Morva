from __future__ import annotations

from datetime import datetime, timezone

import pytest

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceItem,
    build_registry,
)
from morva.runtime.disaster_recovery import RecoveryDrillEvidence
from morva.runtime.dr_evidence_bridge import (
    DisasterRecoveryEvidenceBridgeError,
    build_disaster_recovery_evidence_binding,
)

NOW = datetime.fromisoformat("2026-09-22T12:00:00+00:00")


def _authority(**overrides):
    payload = {
        "intake_version": 1,
        "evidence_id": "DR-001",
        "source_type": "dr_report",
        "source_uri": "https://authority.example/dr/2026-09",
        "source_sha256": "0" * 64,
        "issuer": "dr-authority",
        "population_scope": "enterprise",
        "effective_from": "2026-01-01T00:00:00+00:00",
        "effective_to": "2027-01-01T00:00:00+00:00",
        "status": "accepted",
        "approved_by": "dr-approver",
        "approved_at": "2026-09-20T10:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
    }
    payload.update(overrides)
    return AuthoritativeEvidenceItem(**payload)


def _dr(**overrides):
    payload = {
        "drill_id": "DRILL-001",
        "backup_id": "BACKUP-001",
        "backup_sha256": "a" * 64,
        "restore_started_at": datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc),
        "restore_completed_at": datetime(2026, 9, 21, 10, 30, tzinfo=timezone.utc),
        "target_rpo_seconds": 3600,
        "target_rto_seconds": 7200,
        "measured_rpo_seconds": 900,
        "measured_rto_seconds": 1800,
        "wal_replayed": True,
        "point_in_time_verified": True,
        "encrypted_backup_verified": True,
        "operator": "dr-operator",
        "evidence_uri": "https://authority.example/dr/2026-09",
    }
    payload.update(overrides)
    return RecoveryDrillEvidence(**payload)


def _registry(source_sha256: str | None = None):
    evidence = _dr()
    source_sha = source_sha256 or evidence.fingerprint
    return build_registry(
        (
            _authority(source_sha256=source_sha),
        ),
        registered_at=NOW,
    )


def test_dr_binding_accepts_release_ready_evidence():
    evidence = _dr()
    binding = build_disaster_recovery_evidence_binding(
        evidence,
        _registry(evidence.fingerprint),
        authoritative_evidence_id="DR-001",
        bound_by="dr-binder",
        bound_at=NOW,
    )
    assert binding.release_ready
    assert binding.backup_id == "BACKUP-001"
    assert len(binding.fingerprint) == 64


def test_non_ready_dr_is_rejected():
    with pytest.raises(DisasterRecoveryEvidenceBridgeError, match="release-ready"):
        build_disaster_recovery_evidence_binding(
            _dr(measured_rto_seconds=8000),
            _registry(),
            authoritative_evidence_id="DR-001",
            bound_by="dr-binder",
            bound_at=NOW,
        )


def test_wrong_source_type_is_rejected():
    with pytest.raises(DisasterRecoveryEvidenceBridgeError, match="dr_report"):
        build_disaster_recovery_evidence_binding(
            _dr(),
            _registry(_dr().fingerprint),
            authoritative_evidence_id="DR-001",
            bound_by="dr-binder",
            bound_at=NOW,
        )


def test_fingerprint_mismatch_is_rejected():
    with pytest.raises(DisasterRecoveryEvidenceBridgeError, match="fingerprint"):
        build_disaster_recovery_evidence_binding(
            _dr(),
            _registry("1" * 64),
            authoritative_evidence_id="DR-001",
            bound_by="dr-binder",
            bound_at=NOW,
        )


def test_expired_authority_is_rejected():
    with pytest.raises(DisasterRecoveryEvidenceBridgeError, match="expired"):
        build_disaster_recovery_evidence_binding(
            _dr(),
            build_registry(
                (_authority(source_sha256=_dr().fingerprint, expires_at="2026-09-21T23:59:59+00:00"),),
                registered_at=NOW,
            ),
            authoritative_evidence_id="DR-001",
            bound_by="dr-binder",
            bound_at=NOW,
        )
