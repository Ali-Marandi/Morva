from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475Record,
)
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479PersistenceError,
    IndependentM477VerificationReceiptM479Record,
)
from morva.runtime.independent_historical_m4_75_verification_receipt_history_integrity_m4_78 import (
    independently_verify_historical_m4_75_verification_receipt_history_integrity,
)


class IndependentM477VerificationReceiptM480Error(ValueError):
    """Raised when an M4.79 receipt fails independent M4.80 verification."""


@dataclass(frozen=True, slots=True)
class IndependentM477VerificationReceiptM480:
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
                raise IndependentM477VerificationReceiptM480Error(
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
            raise IndependentM477VerificationReceiptM480Error(
                "M4.80 verification fingerprint mismatch"
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


def independently_verify_m4_79_verification_receipt(
    *,
    receipt: IndependentM477VerificationReceiptM479Record,
    snapshot: HistoricalM475VerificationReceiptHistoryIntegrityRecord,
    source_records: list[HistoricalM472VerificationReceiptM475Record],
) -> IndependentM477VerificationReceiptM480:
    try:
        stored = receipt.to_verification()
    except IndependentM477VerificationReceiptM479PersistenceError as exc:
        raise IndependentM477VerificationReceiptM480Error(
            "persisted M4.79 verification receipt is structurally invalid"
        ) from exc

    if receipt.snapshot_id != snapshot.id:
        raise IndependentM477VerificationReceiptM480Error(
            "M4.79 receipt snapshot binding is invalid"
        )

    reconstructed = independently_verify_historical_m4_75_verification_receipt_history_integrity(
        snapshot=snapshot,
        source_records=source_records,
    )

    blockers: list[str] = []
    if stored.snapshot_id != reconstructed.snapshot_id:
        blockers.append("M479_SNAPSHOT_ID_MISMATCH")
    if (
        stored.verification_fingerprint.lower()
        != reconstructed.verification_fingerprint.lower()
    ):
        blockers.append("M479_VERIFICATION_FINGERPRINT_MISMATCH")
    if (
        stored.persisted_fingerprint.lower()
        != reconstructed.persisted_fingerprint.lower()
    ):
        blockers.append("M479_PERSISTED_FINGERPRINT_MISMATCH")
    if (
        stored.reconstructed_fingerprint.lower()
        != reconstructed.reconstructed_fingerprint.lower()
    ):
        blockers.append("M479_RECONSTRUCTED_FINGERPRINT_MISMATCH")
    if stored.persisted_valid != reconstructed.valid:
        blockers.append("M479_VALIDITY_MISMATCH")

    blocker_tuple = tuple(blockers)
    valid = not blocker_tuple

    return IndependentM477VerificationReceiptM480(
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
