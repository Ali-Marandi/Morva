from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceRegistry,
)
from morva.runtime.disaster_recovery import RecoveryDrillEvidence


class DisasterRecoveryEvidenceBridgeError(ValueError):
    """Raised when DR drill evidence cannot bind to authoritative evidence."""


@dataclass(frozen=True, slots=True)
class DisasterRecoveryEvidenceBinding:
    binding_version: int
    drill_id: str
    authoritative_evidence_id: str
    backup_id: str
    backup_sha256: str
    evidence_uri: str
    rpo_compliant: bool
    rto_compliant: bool
    wal_replayed: bool
    point_in_time_verified: bool
    encrypted_backup_verified: bool
    bound_by: str
    bound_at: datetime

    def __post_init__(self) -> None:
        if self.binding_version != 1:
            raise DisasterRecoveryEvidenceBridgeError(
                "unsupported disaster-recovery binding version"
            )
        for name, value in (
            ("drill_id", self.drill_id),
            ("authoritative_evidence_id", self.authoritative_evidence_id),
            ("backup_id", self.backup_id),
            ("evidence_uri", self.evidence_uri),
            ("bound_by", self.bound_by),
        ):
            if not value.strip():
                raise DisasterRecoveryEvidenceBridgeError(f"{name} is required")
        if len(self.backup_sha256) != 64 or any(
            char not in "0123456789abcdef"
            for char in self.backup_sha256.lower()
        ):
            raise DisasterRecoveryEvidenceBridgeError(
                "backup_sha256 must be SHA-256"
            )
        if self.bound_at.tzinfo is None:
            raise DisasterRecoveryEvidenceBridgeError(
                "bound_at must be timezone-aware"
            )

    @property
    def release_ready(self) -> bool:
        return all(
            (
                self.rpo_compliant,
                self.rto_compliant,
                self.wal_replayed,
                self.point_in_time_verified,
                self.encrypted_backup_verified,
            )
        )

    @property
    def fingerprint(self) -> str:
        payload = {
            "binding_version": self.binding_version,
            "drill_id": self.drill_id,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "backup_id": self.backup_id,
            "backup_sha256": self.backup_sha256.lower(),
            "evidence_uri": self.evidence_uri,
            "rpo_compliant": self.rpo_compliant,
            "rto_compliant": self.rto_compliant,
            "wal_replayed": self.wal_replayed,
            "point_in_time_verified": self.point_in_time_verified,
            "encrypted_backup_verified": self.encrypted_backup_verified,
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.astimezone(timezone.utc).isoformat(),
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()


def build_disaster_recovery_evidence_binding(
    evidence: RecoveryDrillEvidence,
    registry: AuthoritativeEvidenceRegistry,
    *,
    authoritative_evidence_id: str,
    bound_by: str,
    bound_at: datetime,
) -> DisasterRecoveryEvidenceBinding:
    if not isinstance(evidence, RecoveryDrillEvidence):
        raise DisasterRecoveryEvidenceBridgeError(
            "RecoveryDrillEvidence instance is required"
        )
    if not authoritative_evidence_id.strip():
        raise DisasterRecoveryEvidenceBridgeError(
            "authoritative_evidence_id is required"
        )
    if not bound_by.strip():
        raise DisasterRecoveryEvidenceBridgeError("bound_by is required")
    if bound_at.tzinfo is None:
        raise DisasterRecoveryEvidenceBridgeError(
            "bound_at must be timezone-aware"
        )
    if not evidence.release_ready:
        raise DisasterRecoveryEvidenceBridgeError(
            "disaster-recovery evidence is not release-ready"
        )

    authoritative = next(
        (
            item
            for item in registry.items
            if item.evidence_id == authoritative_evidence_id
        ),
        None,
    )
    if authoritative is None:
        raise DisasterRecoveryEvidenceBridgeError(
            "authoritative DR evidence is not present in registry"
        )
    if authoritative.source_type != "dr_report":
        raise DisasterRecoveryEvidenceBridgeError(
            "DR drill requires dr_report authoritative evidence"
        )
    if authoritative.status != "accepted":
        raise DisasterRecoveryEvidenceBridgeError(
            "authoritative DR evidence must be accepted"
        )
    if authoritative.source_uri.strip() != evidence.evidence_uri.strip():
        raise DisasterRecoveryEvidenceBridgeError(
            "DR evidence URI does not match authoritative evidence"
        )
    if authoritative.source_sha256.lower() != evidence.fingerprint.lower():
        raise DisasterRecoveryEvidenceBridgeError(
            "DR evidence fingerprint does not match authoritative evidence SHA-256"
        )

    bound_at_utc = bound_at.astimezone(timezone.utc)
    if authoritative.approved_at is None:
        raise DisasterRecoveryEvidenceBridgeError(
            "authoritative DR evidence approval is required"
        )
    approved_at = datetime.fromisoformat(authoritative.approved_at)
    if approved_at > bound_at_utc:
        raise DisasterRecoveryEvidenceBridgeError(
            "binding precedes authoritative DR evidence approval"
        )
    effective_from = datetime.fromisoformat(authoritative.effective_from)
    if effective_from > bound_at_utc:
        raise DisasterRecoveryEvidenceBridgeError(
            "authoritative DR evidence is not yet effective"
        )
    if authoritative.effective_to is not None:
        effective_to = datetime.fromisoformat(authoritative.effective_to)
        if effective_to <= bound_at_utc:
            raise DisasterRecoveryEvidenceBridgeError(
                "authoritative DR evidence is no longer effective"
            )
    if authoritative.expires_at is not None:
        expires_at = datetime.fromisoformat(authoritative.expires_at)
        if expires_at <= bound_at_utc:
            raise DisasterRecoveryEvidenceBridgeError(
                "authoritative DR evidence is expired"
            )

    return DisasterRecoveryEvidenceBinding(
        binding_version=1,
        drill_id=evidence.drill_id.strip(),
        authoritative_evidence_id=authoritative_evidence_id.strip(),
        backup_id=evidence.backup_id.strip(),
        backup_sha256=evidence.backup_sha256.lower(),
        evidence_uri=evidence.evidence_uri.strip(),
        rpo_compliant=evidence.rpo_compliant,
        rto_compliant=evidence.rto_compliant,
        wal_replayed=evidence.wal_replayed,
        point_in_time_verified=evidence.point_in_time_verified,
        encrypted_backup_verified=evidence.encrypted_backup_verified,
        bound_by=bound_by.strip(),
        bound_at=bound_at_utc,
    )
