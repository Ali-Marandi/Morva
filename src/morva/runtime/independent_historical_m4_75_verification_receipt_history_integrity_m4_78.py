from __future__ import annotations

from dataclasses import dataclassfrom datetime import datetime

from morva.runtime.historical_integrity_primitives import (
    canonical_sha256,
    canonical_utc_timestamp,
)
from uuid import UUID

from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM475VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475PersistenceError,
    HistoricalM472VerificationReceiptM475Record,
)


class IndependentHistoricalM475VerificationReceiptHistoryIntegrityError(ValueError):
    """Raised when an M4.77 snapshot fails independent M4.78 verification."""


@dataclass(frozen=True, slots=True)
class IndependentHistoricalM475VerificationReceiptHistoryIntegrity:
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
                raise IndependentHistoricalM475VerificationReceiptHistoryIntegrityError(
                    f"{name} must be SHA-256"
                )
        for name, value in (
            ("persisted_record_count", self.persisted_record_count),
            ("reconstructed_record_count", self.reconstructed_record_count),
            ("persisted_valid_count", self.persisted_valid_count),
            ("reconstructed_valid_count", self.reconstructed_valid_count),
        ):
            if value < 0:
                raise IndependentHistoricalM475VerificationReceiptHistoryIntegrityError(
                    f"{name} cannot be negative"
                )
        if self.persisted_valid_count > self.persisted_record_count:
            raise IndependentHistoricalM475VerificationReceiptHistoryIntegrityError(
                "persisted_valid_count is outside persisted_record_count"
            )
        if self.reconstructed_valid_count > self.reconstructed_record_count:
            raise IndependentHistoricalM475VerificationReceiptHistoryIntegrityError(
                "reconstructed_valid_count is outside reconstructed_record_count"
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
            raise IndependentHistoricalM475VerificationReceiptHistoryIntegrityError(
                "independent M4.77 history-integrity verification fingerprint mismatch"
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


def independently_verify_historical_m4_75_verification_receipt_history_integrity(
    *,
    snapshot: HistoricalM475VerificationReceiptHistoryIntegrityRecord,
    source_records: list[HistoricalM472VerificationReceiptM475Record],
) -> IndependentHistoricalM475VerificationReceiptHistoryIntegrity:
    try:
        persisted = snapshot.to_integrity()
    except HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError as exc:
        raise IndependentHistoricalM475VerificationReceiptHistoryIntegrityError(
            "persisted M4.77 receipt-history integrity snapshot is structurally invalid"
        ) from exc

    point_in_time_records = [
        record
        for record in source_records
        if canonical_utc_timestamp(record.created_at) < canonical_utc_timestamp(snapshot.created_at)
    ]
    ordered = sorted(
        point_in_time_records,
        key=lambda record: (canonical_utc_timestamp(record.created_at), str(record.id)),
    )

    canonical_records: list[dict[str, object]] = []
    reconstructed_valid_count = 0
    for record in ordered:
        try:
            verification = record.to_verification()
        except HistoricalM472VerificationReceiptM475PersistenceError as exc:
            raise IndependentHistoricalM475VerificationReceiptHistoryIntegrityError(
                "M4.76 source verification result is structurally invalid"
            ) from exc
        if verification.valid:
            reconstructed_valid_count += 1
        canonical_records.append(
            {
                "id": str(record.id),
                "verification_receipt_id": str(record.verification_receipt_id),
                "persisted_fingerprint": verification.persisted_fingerprint.lower(),
                "reconstructed_fingerprint": verification.reconstructed_fingerprint.lower(),
                "persisted_snapshot_id": str(verification.persisted_snapshot_id),
                "reconstructed_snapshot_id": str(verification.reconstructed_snapshot_id),
                "persisted_valid": verification.persisted_valid,
                "reconstructed_valid": verification.reconstructed_valid,
                "valid": verification.valid,
                "blockers": list(verification.blockers),
                "verification_fingerprint": verification.verification_fingerprint.lower(),
                "recorded_by": record.recorded_by,
                "created_at": canonical_utc_timestamp(record.created_at),
            }
        )

    reconstructed_history_fingerprint = canonical_sha256(canonical_records)
    reconstructed_fingerprint = _aggregate_fingerprint(
        integrity_version=persisted.integrity_version,
        record_count=len(canonical_records),
        valid_count=reconstructed_valid_count,
        history_fingerprint=reconstructed_history_fingerprint,
    )

    blockers: list[str] = []
    if persisted.history_fingerprint.lower() != reconstructed_history_fingerprint:
        blockers.append("M477_HISTORY_FINGERPRINT_MISMATCH")
    if persisted.record_count != len(canonical_records):
        blockers.append("M477_RECORD_COUNT_MISMATCH")
    if persisted.valid_count != reconstructed_valid_count:
        blockers.append("M477_VALID_COUNT_MISMATCH")
    if persisted.fingerprint.lower() != reconstructed_fingerprint:
        blockers.append("M477_INTEGRITY_FINGERPRINT_MISMATCH")

    blocker_tuple = tuple(blockers)
    valid = not blocker_tuple

    return IndependentHistoricalM475VerificationReceiptHistoryIntegrity(
        snapshot_id=snapshot.id,
        persisted_fingerprint=persisted.fingerprint,
        reconstructed_fingerprint=reconstructed_fingerprint,
        persisted_history_fingerprint=persisted.history_fingerprint,
        reconstructed_history_fingerprint=reconstructed_history_fingerprint,
        persisted_record_count=persisted.record_count,
        reconstructed_record_count=len(canonical_records),
        persisted_valid_count=persisted.valid_count,
        reconstructed_valid_count=reconstructed_valid_count,
        valid=valid,
        blockers=blocker_tuple,
        verification_fingerprint=_verification_fingerprint(
            snapshot_id=snapshot.id,
            persisted_fingerprint=persisted.fingerprint,
            reconstructed_fingerprint=reconstructed_fingerprint,
            persisted_history_fingerprint=persisted.history_fingerprint,
            reconstructed_history_fingerprint=reconstructed_history_fingerprint,
            persisted_record_count=persisted.record_count,
            reconstructed_record_count=len(canonical_records),
            persisted_valid_count=persisted.valid_count,
            reconstructed_valid_count=reconstructed_valid_count,
            valid=valid,
            blockers=blocker_tuple,
        ),
    )

def _aggregate_fingerprint(
    *,
    integrity_version: int,
    record_count: int,
    valid_count: int,
    history_fingerprint: str,
) -> str:
    payload = {
        "integrity_version": integrity_version,
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
