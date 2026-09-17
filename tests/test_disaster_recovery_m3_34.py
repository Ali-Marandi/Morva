from datetime import datetime, timedelta, timezone

import pytest

from morva.runtime.disaster_recovery import RecoveryDrillEvidence, RecoveryEvidenceError


START = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
END = START + timedelta(seconds=42)


def evidence(**overrides: object) -> RecoveryDrillEvidence:
    values = {
        "drill_id": "drill-001",
        "backup_id": "backup-001",
        "backup_sha256": "a" * 64,
        "restore_started_at": START,
        "restore_completed_at": END,
        "target_rpo_seconds": 300,
        "target_rto_seconds": 120,
        "measured_rpo_seconds": 90,
        "measured_rto_seconds": 42,
        "wal_replayed": True,
        "point_in_time_verified": True,
        "encrypted_backup_verified": True,
        "operator": "ops@example.invalid",
        "evidence_uri": "evidence://drill-001",
    }
    values.update(overrides)
    return RecoveryDrillEvidence(**values)


def test_release_ready_requires_all_recovery_controls() -> None:
    item = evidence()
    assert item.rpo_compliant
    assert item.rto_compliant
    assert item.release_ready
    item.assert_release_ready()
    assert len(item.fingerprint) == 64


@pytest.mark.parametrize(
    "override",
    [
        {"wal_replayed": False},
        {"point_in_time_verified": False},
        {"encrypted_backup_verified": False},
        {"measured_rpo_seconds": 301},
        {"measured_rto_seconds": 121},
    ],
)
def test_release_gate_fails_closed(override: dict[str, object]) -> None:
    item = evidence(**override)
    assert not item.release_ready
    with pytest.raises(RecoveryEvidenceError):
        item.assert_release_ready()


def test_requires_timezone_aware_timestamps() -> None:
    with pytest.raises(RecoveryEvidenceError):
        evidence(restore_started_at=datetime(2026, 1, 1, 10, 0))


def test_requires_valid_sha256() -> None:
    with pytest.raises(RecoveryEvidenceError):
        evidence(backup_sha256="not-a-digest")


def test_completion_cannot_precede_start() -> None:
    with pytest.raises(RecoveryEvidenceError):
        evidence(restore_completed_at=START - timedelta(seconds=1))
