from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from morva.persistence.historical_m4_57_verification_receipt_history_integrity_m4_58 import (
    HistoricalM457VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM457VerificationReceiptHistoryIntegrityRecord,
    HistoricalM457VerificationReceiptHistoryIntegrityRepository,
)
from morva.persistence.independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
    IndependentHistoricalM455ReceiptVerificationPersistenceError,
    IndependentHistoricalM455ReceiptVerificationRecord,
)
from morva.persistence.independent_historical_m4_58_receipt_history_verification_m4_60 import (
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord,
)


class IndependentHistoricalM460VerificationError(ValueError):
    """Raised when an M4.60 persisted result fails independent verification."""


@dataclass(frozen=True, slots=True)
class IndependentHistoricalM460Verification:
    receipt_id: UUID
    persisted_snapshot_id: UUID
    reconstructed_snapshot_id: UUID
    persisted_verification_fingerprint: str
    reconstructed_verification_fingerprint: str
    persisted_valid: bool
    reconstructed_valid: bool
    blockers: tuple[str, ...]
    verification_fingerprint: str

    def __post_init__(self) -> None:
        for name, value in (
            ("persisted_verification_fingerprint", self.persisted_verification_fingerprint),
            ("reconstructed_verification_fingerprint", self.reconstructed_verification_fingerprint),
            ("verification_fingerprint", self.verification_fingerprint),
        ):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
                raise IndependentHistoricalM460VerificationError(f"{name} must be SHA-256")
        expected = _verification_fingerprint(
            receipt_id=self.receipt_id,
            persisted_snapshot_id=self.persisted_snapshot_id,
            reconstructed_snapshot_id=self.reconstructed_snapshot_id,
            persisted_verification_fingerprint=self.persisted_verification_fingerprint,
            reconstructed_verification_fingerprint=self.reconstructed_verification_fingerprint,
            persisted_valid=self.persisted_valid,
            reconstructed_valid=self.reconstructed_valid,
            blockers=self.blockers,
        )
        if self.verification_fingerprint.lower() != expected:
            raise IndependentHistoricalM460VerificationError(
                "independent M4.60 verification fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "receipt_id": str(self.receipt_id),
            "persisted_snapshot_id": str(self.persisted_snapshot_id),
            "reconstructed_snapshot_id": str(self.reconstructed_snapshot_id),
            "persisted_verification_fingerprint": self.persisted_verification_fingerprint.lower(),
            "reconstructed_verification_fingerprint": self.reconstructed_verification_fingerprint.lower(),
            "persisted_valid": self.persisted_valid,
            "reconstructed_valid": self.reconstructed_valid,
            "blockers": list(self.blockers),
            "verification_fingerprint": self.verification_fingerprint.lower(),
        }


def independently_verify_historical_m4_60_result(
    *,
    receipt: IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord,
    snapshot: HistoricalM457VerificationReceiptHistoryIntegrityRecord,
    source_records: list[IndependentHistoricalM455ReceiptVerificationRecord],
) -> IndependentHistoricalM460Verification:
    try:
        persisted = receipt.to_verification()
    except IndependentHistoricalM458ReceiptHistoryIntegrityReceiptPersistenceError as exc:
        raise IndependentHistoricalM460VerificationError(
            "persisted M4.60 verification receipt is structurally invalid"
        ) from exc

    try:
        from morva.runtime.independent_historical_m4_58_receipt_history_verifier_m4_59 import (
            independently_verify_historical_m4_58_receipt_history_integrity,
        )

        reconstructed = independently_verify_historical_m4_58_receipt_history_integrity(
            snapshot=snapshot,
            source_records=source_records,
        )
    except Exception as exc:
        if isinstance(exc, IndependentHistoricalM460VerificationError):
            raise
        raise IndependentHistoricalM460VerificationError(
            "M4.59 independent reconstruction failed"
        ) from exc

    blockers: list[str] = []
    if persisted.snapshot_id != reconstructed.snapshot_id:
        blockers.append("M460_SNAPSHOT_ID_MISMATCH")
    if (
        persisted.verification_fingerprint.lower()
        != reconstructed.verification_fingerprint.lower()
    ):
        blockers.append("M460_VERIFICATION_FINGERPRINT_MISMATCH")
    if persisted.valid != reconstructed.valid:
        blockers.append("M460_VALIDITY_MISMATCH")
    if (
        persisted.persisted_fingerprint.lower()
        != reconstructed.persisted_fingerprint.lower()
        or persisted.reconstructed_fingerprint.lower()
        != reconstructed.reconstructed_fingerprint.lower()
        or persisted.persisted_history_fingerprint.lower()
        != reconstructed.persisted_history_fingerprint.lower()
        or persisted.reconstructed_history_fingerprint.lower()
        != reconstructed.reconstructed_history_fingerprint.lower()
        or persisted.persisted_record_count != reconstructed.persisted_record_count
        or persisted.reconstructed_record_count != reconstructed.reconstructed_record_count
        or persisted.persisted_valid_count != reconstructed.persisted_valid_count
        or persisted.reconstructed_valid_count != reconstructed.reconstructed_valid_count
        or tuple(persisted.blockers) != tuple(reconstructed.blockers)
    ):
        blockers.append("M460_VERIFICATION_RESULT_MISMATCH")

    blocker_tuple = tuple(dict.fromkeys(blockers))
    return IndependentHistoricalM460Verification(
        receipt_id=receipt.id,
        persisted_snapshot_id=persisted.snapshot_id,
        reconstructed_snapshot_id=reconstructed.snapshot_id,
        persisted_verification_fingerprint=persisted.verification_fingerprint,
        reconstructed_verification_fingerprint=reconstructed.verification_fingerprint,
        persisted_valid=persisted.valid,
        reconstructed_valid=reconstructed.valid,
        blockers=blocker_tuple,
        verification_fingerprint=_verification_fingerprint(
            receipt_id=receipt.id,
            persisted_snapshot_id=persisted.snapshot_id,
            reconstructed_snapshot_id=reconstructed.snapshot_id,
            persisted_verification_fingerprint=persisted.verification_fingerprint,
            reconstructed_verification_fingerprint=reconstructed.verification_fingerprint,
            persisted_valid=persisted.valid,
            reconstructed_valid=reconstructed.valid,
            blockers=blocker_tuple,
        ),
    )


def _verification_fingerprint(
    *,
    receipt_id: UUID,
    persisted_snapshot_id: UUID,
    reconstructed_snapshot_id: UUID,
    persisted_verification_fingerprint: str,
    reconstructed_verification_fingerprint: str,
    persisted_valid: bool,
    reconstructed_valid: bool,
    blockers: tuple[str, ...],
) -> str:
    payload = {
        "verification_version": 1,
        "receipt_id": str(receipt_id),
        "persisted_snapshot_id": str(persisted_snapshot_id),
        "reconstructed_snapshot_id": str(reconstructed_snapshot_id),
        "persisted_verification_fingerprint": persisted_verification_fingerprint.lower(),
        "reconstructed_verification_fingerprint": reconstructed_verification_fingerprint.lower(),
        "persisted_valid": persisted_valid,
        "reconstructed_valid": reconstructed_valid,
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
