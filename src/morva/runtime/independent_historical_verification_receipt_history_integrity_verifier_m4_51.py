from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID

from morva.persistence.historical_independent_verification_receipt_history_integrity_m4_50 import (
    HistoricalIndependentVerificationReceiptHistoryIntegrityError,
    HistoricalIndependentVerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_freshness_verification_history_integrity_receipts_m4_49 import (
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord,
)


class IndependentHistoricalVerificationReceiptHistoryIntegrityError(ValueError):
    """Raised when an M4.50 history-integrity snapshot fails independent verification."""


@dataclass(frozen=True, slots=True)
class IndependentHistoricalVerificationReceiptHistoryIntegrity:
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
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise IndependentHistoricalVerificationReceiptHistoryIntegrityError(
                    f"{name} must be SHA-256"
                )
        for name, value in (
            ("persisted_record_count", self.persisted_record_count),
            ("reconstructed_record_count", self.reconstructed_record_count),
            ("persisted_valid_count", self.persisted_valid_count),
            ("reconstructed_valid_count", self.reconstructed_valid_count),
        ):
            if value < 0:
                raise IndependentHistoricalVerificationReceiptHistoryIntegrityError(
                    f"{name} cannot be negative"
                )
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
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityError(
                "independent M4.50 receipt-history verification fingerprint mismatch"
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


def independently_verify_historical_independent_verification_receipt_history_integrity(
    *,
    snapshot: HistoricalIndependentVerificationReceiptHistoryIntegrityRecord,
    source_records: list[IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptRecord],
) -> IndependentHistoricalVerificationReceiptHistoryIntegrity:
    try:
        persisted = snapshot.to_integrity()
    except HistoricalIndependentVerificationReceiptHistoryIntegrityError as exc:
        raise IndependentHistoricalVerificationReceiptHistoryIntegrityError(
            "persisted M4.50 receipt-history integrity snapshot is structurally invalid"
        ) from exc

    point_in_time_records = [
        record
        for record in source_records
        if _timestamp(record.created_at) < _timestamp(snapshot.created_at)
    ]
    ordered = sorted(
        point_in_time_records,
        key=lambda record: (_timestamp(record.created_at), str(record.id)),
    )

    canonical_records: list[dict[str, object]] = []
    valid_count = 0
    for record in ordered:
        try:
            verification = record.to_verification()
        except IndependentHistoricalFreshnessVerificationHistoryIntegrityReceiptPersistenceError as exc:
            raise IndependentHistoricalVerificationReceiptHistoryIntegrityError(
                "M4.49 source receipt-history record is structurally invalid"
            ) from exc
        if verification.valid:
            valid_count += 1
        canonical_records.append(
            {
                "id": str(record.id),
                "snapshot_id": str(record.snapshot_id),
                "persisted_fingerprint": verification.persisted_fingerprint.lower(),
                "reconstructed_fingerprint": verification.reconstructed_fingerprint.lower(),
                "persisted_history_fingerprint": verification.persisted_history_fingerprint.lower(),
                "reconstructed_history_fingerprint": verification.reconstructed_history_fingerprint.lower(),
                "persisted_record_count": verification.persisted_record_count,
                "reconstructed_record_count": verification.reconstructed_record_count,
                "persisted_valid_count": verification.persisted_valid_count,
                "reconstructed_valid_count": verification.reconstructed_valid_count,
                "persisted_chain_valid_count": verification.persisted_chain_valid_count,
                "reconstructed_chain_valid_count": verification.reconstructed_chain_valid_count,
                "valid": verification.valid,
                "blockers": list(verification.blockers),
                "verification_fingerprint": verification.verification_fingerprint.lower(),
                "recorded_by": record.recorded_by,
                "created_at": _timestamp(record.created_at),
            }
        )

    reconstructed_history_fingerprint = sha256(
        json.dumps(
            canonical_records,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    reconstructed_record_count = len(canonical_records)
    reconstructed_fingerprint = _history_fingerprint(
        record_count=reconstructed_record_count,
        valid_count=valid_count,
        history_fingerprint=reconstructed_history_fingerprint,
    )

    blockers: list[str] = []
    if persisted.integrity_version != 1:
        blockers.append("M450_INTEGRITY_VERSION_MISMATCH")
    if persisted.history_fingerprint.lower() != reconstructed_history_fingerprint:
        blockers.append("M450_HISTORY_FINGERPRINT_MISMATCH")
    if persisted.record_count != reconstructed_record_count:
        blockers.append("M450_RECORD_COUNT_MISMATCH")
    if persisted.valid_count != valid_count:
        blockers.append("M450_VALID_COUNT_MISMATCH")
    if persisted.fingerprint.lower() != reconstructed_fingerprint:
        blockers.append("M450_INTEGRITY_FINGERPRINT_MISMATCH")

    blocker_tuple = tuple(blockers)
    valid = not blocker_tuple
    return IndependentHistoricalVerificationReceiptHistoryIntegrity(
        snapshot_id=snapshot.id,
        persisted_fingerprint=persisted.fingerprint,
        reconstructed_fingerprint=reconstructed_fingerprint,
        persisted_history_fingerprint=persisted.history_fingerprint,
        reconstructed_history_fingerprint=reconstructed_history_fingerprint,
        persisted_record_count=persisted.record_count,
        reconstructed_record_count=reconstructed_record_count,
        persisted_valid_count=persisted.valid_count,
        reconstructed_valid_count=valid_count,
        valid=valid,
        blockers=blocker_tuple,
        verification_fingerprint=_verification_fingerprint(
            snapshot_id=snapshot.id,
            persisted_fingerprint=persisted.fingerprint,
            reconstructed_fingerprint=reconstructed_fingerprint,
            persisted_history_fingerprint=persisted.history_fingerprint,
            reconstructed_history_fingerprint=reconstructed_history_fingerprint,
            persisted_record_count=persisted.record_count,
            reconstructed_record_count=reconstructed_record_count,
            persisted_valid_count=persisted.valid_count,
            reconstructed_valid_count=valid_count,
            valid=valid,
            blockers=blocker_tuple,
        ),
    )


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _history_fingerprint(
    *,
    record_count: int,
    valid_count: int,
    history_fingerprint: str,
) -> str:
    payload = {
        "integrity_version": 1,
        "record_count": record_count,
        "valid_count": valid_count,
        "history_fingerprint": history_fingerprint.lower(),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


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
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
