"""Independently verify M4.75 point-in-time M4.74 history snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID

from morva.persistence.historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM474VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
)
from morva.runtime.historical_m4_74_verification_receipt_history_integrity_m4_75 import (
    build_historical_m4_74_verification_receipt_history_integrity,
)


class IndependentHistoricalM475VerificationError(ValueError):
    """Raised when an M4.75 snapshot cannot be independently verified."""


@dataclass(frozen=True, slots=True)
class IndependentHistoricalM475Verification:
    snapshot_id: UUID
    persisted_fingerprint: str
    reconstructed_fingerprint: str
    persisted_history_fingerprint: str
    reconstructed_history_fingerprint: str
    persisted_record_count: int
    reconstructed_record_count: int
    persisted_valid_count: int
    reconstructed_valid_count: int
    valid: bool
    blockers: tuple[str, ...]
    verification_fingerprint: str

    def __post_init__(self) -> None:
        for name, value in (
            ("persisted_fingerprint", self.persisted_fingerprint),
            ("reconstructed_fingerprint", self.reconstructed_fingerprint),
            ("persisted_history_fingerprint", self.persisted_history_fingerprint),
            ("reconstructed_history_fingerprint", self.reconstructed_history_fingerprint),
            ("verification_fingerprint", self.verification_fingerprint),
        ):
            if len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower()):
                raise IndependentHistoricalM475VerificationError(f"{name} must be SHA-256")
        for name, value in (
            ("persisted_record_count", self.persisted_record_count),
            ("reconstructed_record_count", self.reconstructed_record_count),
            ("persisted_valid_count", self.persisted_valid_count),
            ("reconstructed_valid_count", self.reconstructed_valid_count),
        ):
            if value < 0:
                raise IndependentHistoricalM475VerificationError(f"{name} cannot be negative")
        expected = _verification_fingerprint(
            snapshot_id=self.snapshot_id,
            persisted_fingerprint=self.persisted_fingerprint,
            reconstructed_fingerprint=self.reconstructed_fingerprint,
            persisted_history_fingerprint=self.persisted_history_fingerprint,
            reconstructed_history_fingerprint=self.reconstructed_history_fingerprint,
            persisted_record_count=self.persisted_record_count,
            reconstructed_record_count=self.reconstructed_record_count,
            persisted_valid_count=self.persisted_valid_count,
            reconstructed_valid_count=self.reconstructed_valid_count,
            valid=self.valid,
            blockers=self.blockers,
        )
        if self.verification_fingerprint.lower() != expected:
            raise IndependentHistoricalM475VerificationError(
                "independent M4.75 verification fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "snapshot_id": str(self.snapshot_id),
            "persisted_fingerprint": self.persisted_fingerprint.lower(),
            "reconstructed_fingerprint": self.reconstructed_fingerprint.lower(),
            "persisted_history_fingerprint": self.persisted_history_fingerprint.lower(),
            "reconstructed_history_fingerprint": self.reconstructed_history_fingerprint.lower(),
            "persisted_record_count": self.persisted_record_count,
            "reconstructed_record_count": self.reconstructed_record_count,
            "persisted_valid_count": self.persisted_valid_count,
            "reconstructed_valid_count": self.reconstructed_valid_count,
            "valid": self.valid,
            "blockers": list(self.blockers),
            "verification_fingerprint": self.verification_fingerprint.lower(),
        }


def independently_verify_historical_m4_75_snapshot(
    *,
    snapshot: HistoricalM474VerificationReceiptHistoryIntegrityRecord,
    source_records: list[IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord],
) -> IndependentHistoricalM475Verification:
    try:
        persisted = snapshot.to_integrity()
    except HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError as exc:
        raise IndependentHistoricalM475VerificationError(
            "persisted M4.75 snapshot is structurally invalid"
        ) from exc

    point_in_time = [
        record for record in source_records
        if _timestamp(record.created_at) < _timestamp(snapshot.created_at)
    ]
    ordered = sorted(point_in_time, key=lambda r: (_timestamp(r.created_at), str(r.id)))

    try:
        for record in ordered:
            record.to_verification()
        reconstructed = build_historical_m4_74_verification_receipt_history_integrity(ordered)
    except (
        IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
        ValueError,
    ) as exc:
        raise IndependentHistoricalM475VerificationError(
            f"M4.74 point-in-time reconstruction failed: {exc}"
        ) from exc

    blockers: list[str] = []
    if persisted.history_fingerprint.lower() != reconstructed.history_fingerprint.lower():
        blockers.append("M475_HISTORY_FINGERPRINT_MISMATCH")
    if persisted.record_count != reconstructed.record_count:
        blockers.append("M475_RECORD_COUNT_MISMATCH")
    if persisted.valid_count != reconstructed.valid_count:
        blockers.append("M475_VALID_COUNT_MISMATCH")
    if persisted.fingerprint.lower() != reconstructed.fingerprint.lower():
        blockers.append("M475_INTEGRITY_FINGERPRINT_MISMATCH")

    blocker_tuple = tuple(blockers)
    valid = not blocker_tuple
    verification_fingerprint = _verification_fingerprint(
        snapshot_id=snapshot.id,
        persisted_fingerprint=persisted.fingerprint,
        reconstructed_fingerprint=reconstructed.fingerprint,
        persisted_history_fingerprint=persisted.history_fingerprint,
        reconstructed_history_fingerprint=reconstructed.history_fingerprint,
        persisted_record_count=persisted.record_count,
        reconstructed_record_count=reconstructed.record_count,
        persisted_valid_count=persisted.valid_count,
        reconstructed_valid_count=reconstructed.valid_count,
        valid=valid,
        blockers=blocker_tuple,
    )
    return IndependentHistoricalM475Verification(
        snapshot_id=snapshot.id,
        persisted_fingerprint=persisted.fingerprint,
        reconstructed_fingerprint=reconstructed.fingerprint,
        persisted_history_fingerprint=persisted.history_fingerprint,
        reconstructed_history_fingerprint=reconstructed.history_fingerprint,
        persisted_record_count=persisted.record_count,
        reconstructed_record_count=reconstructed.record_count,
        persisted_valid_count=persisted.valid_count,
        reconstructed_valid_count=reconstructed.valid_count,
        valid=valid,
        blockers=blocker_tuple,
        verification_fingerprint=verification_fingerprint,
    )


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _verification_fingerprint(
    *,
    snapshot_id: UUID,
    persisted_fingerprint: str,
    reconstructed_fingerprint: str,
    persisted_history_fingerprint: str,
    reconstructed_history_fingerprint: str,
    persisted_record_count: int,
    reconstructed_record_count: int,
    persisted_valid_count: int,
    reconstructed_valid_count: int,
    valid: bool,
    blockers: tuple[str, ...],
) -> str:
    payload = {
        "verification_version": 1,
        "snapshot_id": str(snapshot_id),
        "persisted_fingerprint": persisted_fingerprint.lower(),
        "reconstructed_fingerprint": reconstructed_fingerprint.lower(),
        "persisted_history_fingerprint": persisted_history_fingerprint.lower(),
        "reconstructed_history_fingerprint": reconstructed_history_fingerprint.lower(),
        "persisted_record_count": persisted_record_count,
        "reconstructed_record_count": reconstructed_record_count,
        "persisted_valid_count": persisted_valid_count,
        "reconstructed_valid_count": reconstructed_valid_count,
        "valid": valid,
        "blockers": list(blockers),
    }
    return sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
