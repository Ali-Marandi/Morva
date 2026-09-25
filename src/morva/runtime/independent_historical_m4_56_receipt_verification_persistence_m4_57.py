from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from morva.persistence.historical_m4_52_verification_receipt_history_integrity_m4_53 import (
    HistoricalM452VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_m4_53_receipt_history_verification_m4_55 import (
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError,
    IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRecord,
)
from morva.persistence.independent_historical_verification_receipt_history_integrity_m4_52 import (
    IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord,
)


class IndependentHistoricalM455ReceiptVerificationPersistenceError(ValueError):
    """Raised when an M4.57 persisted verification result is invalid."""


@dataclass(frozen=True, slots=True)
class IndependentHistoricalM455ReceiptVerificationReceipt:
    verification_receipt_id: UUID
    persisted_snapshot_id: UUID
    reconstructed_snapshot_id: UUID
    persisted_verification_fingerprint: str
    reconstructed_verification_fingerprint: str
    valid: bool
    blockers: tuple[str, ...]
    verification_fingerprint: str

    def __post_init__(self) -> None:
        for name, value in (
            ("persisted_verification_fingerprint", self.persisted_verification_fingerprint),
            ("reconstructed_verification_fingerprint", self.reconstructed_verification_fingerprint),
            ("verification_fingerprint", self.verification_fingerprint),
        ):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
                raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                    f"{name} must be SHA-256"
                )
        expected = _verification_fingerprint(
            verification_receipt_id=self.verification_receipt_id,
            persisted_snapshot_id=self.persisted_snapshot_id,
            reconstructed_snapshot_id=self.reconstructed_snapshot_id,
            persisted_verification_fingerprint=self.persisted_verification_fingerprint,
            reconstructed_verification_fingerprint=self.reconstructed_verification_fingerprint,
            valid=self.valid,
            blockers=self.blockers,
        )
        if self.verification_fingerprint.lower() != expected:
            raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
                "independent M4.56 receipt-verification fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "verification_receipt_id": str(self.verification_receipt_id),
            "persisted_snapshot_id": str(self.persisted_snapshot_id),
            "reconstructed_snapshot_id": str(self.reconstructed_snapshot_id),
            "persisted_verification_fingerprint": self.persisted_verification_fingerprint.lower(),
            "reconstructed_verification_fingerprint": self.reconstructed_verification_fingerprint.lower(),
            "valid": self.valid,
            "blockers": list(self.blockers),
            "verification_fingerprint": self.verification_fingerprint.lower(),
        }


def _verification_fingerprint(*,
    verification_receipt_id: UUID,
    persisted_snapshot_id: UUID,
    reconstructed_snapshot_id: UUID,
    persisted_verification_fingerprint: str,
    reconstructed_verification_fingerprint: str,
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


def independently_persist_m4_56_receipt_verification(
    *,
    receipt: IndependentHistoricalM453ReceiptHistoryIntegrityReceiptRecord,
    snapshot: HistoricalM452VerificationReceiptHistoryIntegrityRecord,
    source_records: list[IndependentHistoricalVerificationReceiptHistoryIntegrityReceiptRecord],
) -> IndependentHistoricalM455ReceiptVerificationReceipt:
    try:
        persisted = receipt.to_verification()
    except IndependentHistoricalM453ReceiptHistoryIntegrityReceiptPersistenceError as exc:
        raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
            "persisted M4.55 verification receipt is structurally invalid"
        ) from exc
    from morva.runtime.independent_historical_m4_55_receipt_verifier_m4_56 import (
        IndependentHistoricalM455ReceiptVerificationError,
        independently_verify_historical_m4_55_receipt,
    )
    try:
        reconstructed = independently_verify_historical_m4_55_receipt(
            receipt=receipt,
            snapshot=snapshot,
            source_records=source_records,
        )
    except IndependentHistoricalM455ReceiptVerificationError as exc:
        raise IndependentHistoricalM455ReceiptVerificationPersistenceError(
            "M4.56 independent reconstruction failed"
        ) from exc
    blockers: list[str] = []
    if persisted.snapshot_id != reconstructed.persisted_snapshot_id:
        blockers.append("M456_SNAPSHOT_ID_MISMATCH")
    if persisted.verification_fingerprint.lower() != reconstructed.persisted_verification_fingerprint.lower():
        blockers.append("M456_VERIFICATION_FINGERPRINT_MISMATCH")
    if persisted != reconstructed:
        blockers.append("M456_VERIFICATION_RESULT_MISMATCH")
    blocker_tuple = tuple(dict.fromkeys(blockers))
    valid = not blocker_tuple
    return IndependentHistoricalM455ReceiptVerificationReceipt(
        verification_receipt_id=receipt.id,
        persisted_snapshot_id=reconstructed.persisted_snapshot_id,
        reconstructed_snapshot_id=reconstructed.reconstructed_snapshot_id,
        persisted_verification_fingerprint=persisted.verification_fingerprint,
        reconstructed_verification_fingerprint=reconstructed.reconstructed_verification_fingerprint,
        valid=valid,
        blockers=blocker_tuple,
        verification_fingerprint=_verification_fingerprint(
            verification_receipt_id=receipt.id,
            persisted_snapshot_id=reconstructed.persisted_snapshot_id,
            reconstructed_snapshot_id=reconstructed.reconstructed_snapshot_id,
            persisted_verification_fingerprint=persisted.verification_fingerprint,
            reconstructed_verification_fingerprint=reconstructed.reconstructed_verification_fingerprint,
            valid=valid,
            blockers=blocker_tuple,
        ),
    )