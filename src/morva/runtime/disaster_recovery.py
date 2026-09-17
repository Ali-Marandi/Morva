from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone


class RecoveryEvidenceError(RuntimeError):
    """Raised when recovery evidence is incomplete or internally inconsistent."""


@dataclass(frozen=True, slots=True)
class RecoveryDrillEvidence:
    """Immutable evidence record for a backup/PITR restore drill."""

    drill_id: str
    backup_id: str
    backup_sha256: str
    restore_started_at: datetime
    restore_completed_at: datetime
    target_rpo_seconds: int
    target_rto_seconds: int
    measured_rpo_seconds: int
    measured_rto_seconds: int
    wal_replayed: bool
    point_in_time_verified: bool
    encrypted_backup_verified: bool
    operator: str
    evidence_uri: str

    def __post_init__(self) -> None:
        if not self.drill_id.strip() or not self.backup_id.strip():
            raise RecoveryEvidenceError("drill_id and backup_id are required")
        if len(self.backup_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.backup_sha256.lower()
        ):
            raise RecoveryEvidenceError("backup_sha256 must be a lowercase SHA-256 hex digest")
        for timestamp in (self.restore_started_at, self.restore_completed_at):
            if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                raise RecoveryEvidenceError("recovery timestamps must be timezone-aware")
        if self.restore_completed_at < self.restore_started_at:
            raise RecoveryEvidenceError("restore completion cannot precede restore start")
        for value, label in (
            (self.target_rpo_seconds, "target_rpo_seconds"),
            (self.target_rto_seconds, "target_rto_seconds"),
            (self.measured_rpo_seconds, "measured_rpo_seconds"),
            (self.measured_rto_seconds, "measured_rto_seconds"),
        ):
            if value < 0:
                raise RecoveryEvidenceError(f"{label} must not be negative")
        if not self.operator.strip() or not self.evidence_uri.strip():
            raise RecoveryEvidenceError("operator and evidence_uri are required")

    @property
    def rto_compliant(self) -> bool:
        return self.measured_rto_seconds <= self.target_rto_seconds

    @property
    def rpo_compliant(self) -> bool:
        return self.measured_rpo_seconds <= self.target_rpo_seconds

    @property
    def release_ready(self) -> bool:
        return all(
            (
                self.rto_compliant,
                self.rpo_compliant,
                self.wal_replayed,
                self.point_in_time_verified,
                self.encrypted_backup_verified,
            )
        )

    @property
    def fingerprint(self) -> str:
        payload = "|".join(
            (
                self.drill_id,
                self.backup_id,
                self.backup_sha256,
                self.restore_started_at.astimezone(timezone.utc).isoformat(),
                self.restore_completed_at.astimezone(timezone.utc).isoformat(),
                str(self.target_rpo_seconds),
                str(self.target_rto_seconds),
                str(self.measured_rpo_seconds),
                str(self.measured_rto_seconds),
                str(self.wal_replayed),
                str(self.point_in_time_verified),
                str(self.encrypted_backup_verified),
                self.operator,
                self.evidence_uri,
            )
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def assert_release_ready(self) -> None:
        if not self.release_ready:
            raise RecoveryEvidenceError(
                "disaster-recovery release gate blocked: "
                "encrypted backup, WAL/PITR verification and RPO/RTO evidence must all pass"
            )
