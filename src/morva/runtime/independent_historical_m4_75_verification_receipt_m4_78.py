"""Independently verify persisted M4.77 M4.76-verification receipts."""

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
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_m4_75_verification_receipts_m4_77 import (
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
    IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
)
from morva.runtime.independent_historical_m4_74_verification_receipt_history_integrity_m4_76 import (
    IndependentHistoricalM474VerificationReceiptHistoryIntegrityError,
    independently_verify_historical_m4_74_verification_receipt_history_integrity,
)


class IndependentHistoricalM475VerificationReceiptM478Error(ValueError):
    """Raised when an M4.77 receipt fails independent M4.78 verification."""


@dataclass(frozen=True, slots=True)
class IndependentHistoricalM475VerificationReceiptM478:
    verification_receipt_id: UUID
    persisted_snapshot_id: UUID
    reconstructed_snapshot_id: UUID
    persisted_verification_fingerprint: str
    reconstructed_verification_fingerprint: str
    persisted_valid: bool
    reconstructed_valid: bool
    persisted_blockers: tuple[str, ...]
    reconstructed_blockers: tuple[str, ...]
    valid: bool
    blockers: tuple[str, ...]
    verification_fingerprint: str

    def __post_init__(self) -> None:
        for name, value in (
            (
                "persisted_verification_fingerprint",
                self.persisted_verification_fingerprint,
            ),
            (
                "reconstructed_verification_fingerprint",
                self.reconstructed_verification_fingerprint,
            ),
            ("verification_fingerprint", self.verification_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise IndependentHistoricalM475VerificationReceiptM478Error(
                    f"{name} must be SHA-256"
                )

        expected = _verification_fingerprint(
            verification_receipt_id=self.verification_receipt_id,
            persisted_snapshot_id=self.persisted_snapshot_id,
            reconstructed_snapshot_id=self.reconstructed_snapshot_id,
            persisted_verification_fingerprint=self.persisted_verification_fingerprint,
            reconstructed_verification_fingerprint=self.reconstructed_verification_fingerprint,
            persisted_valid=self.persisted_valid,
            reconstructed_valid=self.reconstructed_valid,
            persisted_blockers=self.persisted_blockers,
            reconstructed_blockers=self.reconstructed_blockers,
            valid=self.valid,
            blockers=self.blockers,
        )
        if self.verification_fingerprint.lower() != expected:
            raise IndependentHistoricalM475VerificationReceiptM478Error(
                "independent M4.78 verification fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "verification_receipt_id": str(self.verification_receipt_id),
            "persisted_snapshot_id": str(self.persisted_snapshot_id),
            "reconstructed_snapshot_id": str(self.reconstructed_snapshot_id),
            "persisted_verification_fingerprint": self.persisted_verification_fingerprint.lower(),
            "reconstructed_verification_fingerprint": self.reconstructed_verification_fingerprint.lower(),
            "persisted_valid": self.persisted_valid,
            "reconstructed_valid": self.reconstructed_valid,
            "persisted_blockers": list(self.persisted_blockers),
            "reconstructed_blockers": list(self.reconstructed_blockers),
            "valid": self.valid,
            "blockers": list(self.blockers),
            "verification_fingerprint": self.verification_fingerprint.lower(),
        }


def independently_verify_historical_m4_75_verification_receipt_m4_77(
    *,
    receipt: IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
    snapshot: HistoricalM474VerificationReceiptHistoryIntegrityRecord,
    source_records: list[IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord],
    source_repository: IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
) -> IndependentHistoricalM475VerificationReceiptM478:
    try:
        persisted = receipt.to_verification()
    except IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError as exc:
        raise IndependentHistoricalM475VerificationReceiptM478Error(
            "persisted M4.77 verification receipt is structurally invalid"
        ) from exc

    try:
        snapshot.to_integrity()
    except HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError as exc:
        raise IndependentHistoricalM475VerificationReceiptM478Error(
            "persisted M4.75 source snapshot is structurally invalid"
        ) from exc

    ordered = sorted(
        (
            record
            for record in source_records
            if _timestamp(record.created_at) < _timestamp(snapshot.created_at)
        ),
        key=lambda record: (_timestamp(record.created_at), str(record.id)),
    )

    try:
        for source_record in ordered:
            source_repository.verify(source_record.id)
        reconstructed = independently_verify_historical_m4_74_verification_receipt_history_integrity(
            snapshot=snapshot,
            source_records=ordered,
        )
    except (
        IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
        IndependentHistoricalM474VerificationReceiptHistoryIntegrityError,
    ) as exc:
        raise IndependentHistoricalM475VerificationReceiptM478Error(
            f"M4.78 independent source reconstruction failed: {exc}"
        ) from exc

    blockers: list[str] = []
    if persisted.snapshot_id != reconstructed.snapshot_id:
        blockers.append("M478_SNAPSHOT_BINDING_MISMATCH")
    if persisted.persisted_fingerprint.lower() != reconstructed.persisted_fingerprint.lower():
        blockers.append("M478_PERSISTED_FINGERPRINT_MISMATCH")
    if persisted.reconstructed_fingerprint.lower() != reconstructed.reconstructed_fingerprint.lower():
        blockers.append("M478_RECONSTRUCTED_FINGERPRINT_MISMATCH")
    if (
        persisted.persisted_history_fingerprint.lower()
        != reconstructed.persisted_history_fingerprint.lower()
        or persisted.reconstructed_history_fingerprint.lower()
        != reconstructed.reconstructed_history_fingerprint.lower()
    ):
        blockers.append("M478_HISTORY_FINGERPRINT_MISMATCH")
    if (
        persisted.persisted_record_count != reconstructed.persisted_record_count
        or persisted.reconstructed_record_count != reconstructed.reconstructed_record_count
    ):
        blockers.append("M478_RECORD_COUNT_MISMATCH")
    if (
        persisted.persisted_valid_count != reconstructed.persisted_valid_count
        or persisted.reconstructed_valid_count != reconstructed.reconstructed_valid_count
    ):
        blockers.append("M478_VALID_COUNT_MISMATCH")
    if persisted.valid != reconstructed.valid:
        blockers.append("M478_VALIDITY_MISMATCH")
    if tuple(persisted.blockers) != tuple(reconstructed.blockers):
        blockers.append("M478_BLOCKERS_MISMATCH")
    if (
        persisted.verification_fingerprint.lower()
        != reconstructed.verification_fingerprint.lower()
    ):
        blockers.append("M478_VERIFICATION_FINGERPRINT_MISMATCH")

    blocker_tuple = tuple(blockers)
    valid = not blocker_tuple
    return IndependentHistoricalM475VerificationReceiptM478(
        verification_receipt_id=receipt.id,
        persisted_snapshot_id=persisted.snapshot_id,
        reconstructed_snapshot_id=reconstructed.snapshot_id,
        persisted_verification_fingerprint=persisted.verification_fingerprint,
        reconstructed_verification_fingerprint=reconstructed.verification_fingerprint,
        persisted_valid=persisted.valid,
        reconstructed_valid=reconstructed.valid,
        persisted_blockers=tuple(persisted.blockers),
        reconstructed_blockers=tuple(reconstructed.blockers),
        valid=valid,
        blockers=blocker_tuple,
        verification_fingerprint=_verification_fingerprint(
            verification_receipt_id=receipt.id,
            persisted_snapshot_id=persisted.snapshot_id,
            reconstructed_snapshot_id=reconstructed.snapshot_id,
            persisted_verification_fingerprint=persisted.verification_fingerprint,
            reconstructed_verification_fingerprint=reconstructed.verification_fingerprint,
            persisted_valid=persisted.valid,
            reconstructed_valid=reconstructed.valid,
            persisted_blockers=tuple(persisted.blockers),
            reconstructed_blockers=tuple(reconstructed.blockers),
            valid=valid,
            blockers=blocker_tuple,
        ),
    )


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _verification_fingerprint(
    *,
    verification_receipt_id: UUID,
    persisted_snapshot_id: UUID,
    reconstructed_snapshot_id: UUID,
    persisted_verification_fingerprint: str,
    reconstructed_verification_fingerprint: str,
    persisted_valid: bool,
    reconstructed_valid: bool,
    persisted_blockers: tuple[str, ...],
    reconstructed_blockers: tuple[str, ...],
    valid: bool,
    blockers: tuple[str, ...],
) -> str:
    payload = {
        "verification_version": 1,
        "verification_receipt_id": str(verification_receipt_id),
        "persisted_snapshot_id": str(persisted_snapshot_id),
        "reconstructed_snapshot_id": str(reconstructed_snapshot_id),
        "persisted_verification_fingerprint": persisted_verification_fingerprint.lower(),
        "reconstructed_verification_fingerprint": reconstructed_verification_fingerprint.lower(),
        "persisted_valid": persisted_valid,
        "reconstructed_valid": reconstructed_valid,
        "persisted_blockers": list(persisted_blockers),
        "reconstructed_blockers": list(reconstructed_blockers),
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
