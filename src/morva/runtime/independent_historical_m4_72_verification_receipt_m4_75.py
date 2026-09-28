from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID

from morva.persistence.historical_m4_71_verification_history_integrity_m4_72 import (
    HistoricalM471VerificationHistoryIntegrityPersistenceError,
    HistoricalM471VerificationHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_m4_69_verification_receipts_m4_71 import (
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord,
    IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository,
)
from morva.persistence.independent_historical_m4_72_verification_receipts_m4_74 import (
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
)
from morva.runtime.independent_historical_m4_71_verification_history_integrity_m4_73 import (
    IndependentHistoricalM471VerificationHistoryIntegrityError,
    independently_verify_historical_m4_71_verification_history_integrity,
)


class IndependentHistoricalM472VerificationReceiptVerificationError(ValueError):
    """Raised when an M4.74 receipt fails independent M4.75 verification."""


@dataclass(frozen=True, slots=True)
class IndependentHistoricalM472VerificationReceiptVerification:
    verification_receipt_id: UUID
    persisted_fingerprint: str
    reconstructed_fingerprint: str
    persisted_snapshot_id: UUID
    reconstructed_snapshot_id: UUID
    persisted_valid: bool
    reconstructed_valid: bool
    valid: bool
    blockers: tuple[str, ...]
    verification_fingerprint: str

    def __post_init__(self) -> None:
        for name, value in (
            ("persisted_fingerprint", self.persisted_fingerprint),
            ("reconstructed_fingerprint", self.reconstructed_fingerprint),
            ("verification_fingerprint", self.verification_fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise IndependentHistoricalM472VerificationReceiptVerificationError(
                    f"{name} must be SHA-256"
                )
        expected = _verification_fingerprint(
            verification_receipt_id=self.verification_receipt_id,
            persisted_fingerprint=self.persisted_fingerprint,
            reconstructed_fingerprint=self.reconstructed_fingerprint,
            persisted_snapshot_id=self.persisted_snapshot_id,
            reconstructed_snapshot_id=self.reconstructed_snapshot_id,
            persisted_valid=self.persisted_valid,
            reconstructed_valid=self.reconstructed_valid,
            valid=self.valid,
            blockers=self.blockers,
        )
        if self.verification_fingerprint.lower() != expected:
            raise IndependentHistoricalM472VerificationReceiptVerificationError(
                "M4.75 verification fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "verification_receipt_id": str(self.verification_receipt_id),
            "persisted_fingerprint": self.persisted_fingerprint.lower(),
            "reconstructed_fingerprint": self.reconstructed_fingerprint.lower(),
            "persisted_snapshot_id": str(self.persisted_snapshot_id),
            "reconstructed_snapshot_id": str(self.reconstructed_snapshot_id),
            "persisted_valid": self.persisted_valid,
            "reconstructed_valid": self.reconstructed_valid,
            "valid": self.valid,
            "blockers": list(self.blockers),
            "verification_fingerprint": self.verification_fingerprint.lower(),
        }


def independently_verify_historical_m4_72_verification_receipt(
    *,
    receipt: IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord,
    snapshot: HistoricalM471VerificationHistoryIntegrityRecord,
    source_records: list[IndependentHistoricalM469VerificationHistoryIntegrityReceiptRecord],
    source_repository: IndependentHistoricalM469VerificationHistoryIntegrityReceiptRepository,
) -> IndependentHistoricalM472VerificationReceiptVerification:
    try:
        stored = receipt.to_verification()
    except IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError as exc:
        raise IndependentHistoricalM472VerificationReceiptVerificationError(
            "persisted M4.74 verification receipt is structurally invalid"
        ) from exc

    if receipt.snapshot_id != snapshot.id:
        raise IndependentHistoricalM472VerificationReceiptVerificationError(
            "M4.74 receipt snapshot binding is invalid"
        )
    try:
        snapshot.to_integrity()
    except HistoricalM471VerificationHistoryIntegrityPersistenceError as exc:
        raise IndependentHistoricalM472VerificationReceiptVerificationError(
            "M4.72 source snapshot is structurally invalid"
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
    try:
        for source_record in ordered:
            source_repository.verify(source_record.id)
        reconstructed = independently_verify_historical_m4_71_verification_history_integrity(
            snapshot=snapshot,
            source_records=ordered,
        )
    except (
        IndependentHistoricalM469VerificationHistoryIntegrityReceiptPersistenceError,
        IndependentHistoricalM471VerificationHistoryIntegrityError,
    ) as exc:
        raise IndependentHistoricalM472VerificationReceiptVerificationError(
            f"M4.73 independent reconstruction failed: {exc}"
        ) from exc

    blockers: list[str] = []
    if stored.snapshot_id != reconstructed.snapshot_id:
        blockers.append("M474_SNAPSHOT_ID_MISMATCH")
    if stored.verification_fingerprint.lower() != reconstructed.verification_fingerprint.lower():
        blockers.append("M474_VERIFICATION_FINGERPRINT_MISMATCH")
    if stored.persisted_fingerprint.lower() != reconstructed.persisted_fingerprint.lower():
        blockers.append("M474_PERSISTED_FINGERPRINT_MISMATCH")
    if stored.reconstructed_fingerprint.lower() != reconstructed.reconstructed_fingerprint.lower():
        blockers.append("M474_RECONSTRUCTED_FINGERPRINT_MISMATCH")
    if stored.persisted_valid != reconstructed.valid:
        blockers.append("M474_VALIDITY_MISMATCH")

    blocker_tuple = tuple(blockers)
    valid = not blocker_tuple
    return IndependentHistoricalM472VerificationReceiptVerification(
        verification_receipt_id=receipt.id,
        persisted_fingerprint=stored.verification_fingerprint,
        reconstructed_fingerprint=reconstructed.verification_fingerprint,
        persisted_snapshot_id=stored.snapshot_id,
        reconstructed_snapshot_id=reconstructed.snapshot_id,
        persisted_valid=stored.valid,
        reconstructed_valid=reconstructed.valid,
        valid=valid,
        blockers=blocker_tuple,
        verification_fingerprint=_verification_fingerprint(
            verification_receipt_id=receipt.id,
            persisted_fingerprint=stored.verification_fingerprint,
            reconstructed_fingerprint=reconstructed.verification_fingerprint,
            persisted_snapshot_id=stored.snapshot_id,
            reconstructed_snapshot_id=reconstructed.snapshot_id,
            persisted_valid=stored.valid,
            reconstructed_valid=reconstructed.valid,
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
    persisted_fingerprint: str,
    reconstructed_fingerprint: str,
    persisted_snapshot_id: UUID,
    reconstructed_snapshot_id: UUID,
    persisted_valid: bool,
    reconstructed_valid: bool,
    valid: bool,
    blockers: tuple[str, ...],
) -> str:
    payload = {
        "verification_version": 1,
        "verification_receipt_id": str(verification_receipt_id),
        "persisted_fingerprint": persisted_fingerprint.lower(),
        "reconstructed_fingerprint": reconstructed_fingerprint.lower(),
        "persisted_snapshot_id": str(persisted_snapshot_id),
        "reconstructed_snapshot_id": str(reconstructed_snapshot_id),
        "persisted_valid": persisted_valid,
        "reconstructed_valid": reconstructed_valid,
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
