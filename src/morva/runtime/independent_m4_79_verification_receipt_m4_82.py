from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475PersistenceError,
    HistoricalM472VerificationReceiptM475Record,
)
from morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77 import (
    HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
    HistoricalM475VerificationReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479PersistenceError,
    IndependentM477VerificationReceiptM479Record,
)
from morva.persistence.independent_m4_79_verification_receipts_m4_81 import (
    IndependentM479VerificationReceiptM481PersistenceError,
    IndependentM479VerificationReceiptM481Record,
)
from morva.runtime.independent_m4_77_verification_receipt_m4_80 import (
    IndependentM477VerificationReceiptM480Error,
    independently_verify_m4_79_verification_receipt,
)


class IndependentM481VerificationReceiptM482Error(ValueError):
    """Raised when an M4.81 verification receipt fails independent M4.82 verification."""


@dataclass(frozen=True, slots=True)
class IndependentM481VerificationReceiptM482:
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
                raise IndependentM481VerificationReceiptM482Error(
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
            raise IndependentM481VerificationReceiptM482Error(
                "M4.82 verification fingerprint mismatch"
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


def independently_verify_m4_81_verification_receipt(
    *,
    receipt: IndependentM479VerificationReceiptM481Record,
    source_receipt: IndependentM477VerificationReceiptM479Record,
    snapshot: HistoricalM475VerificationReceiptHistoryIntegrityRecord,
    source_records: list[HistoricalM472VerificationReceiptM475Record],
) -> IndependentM481VerificationReceiptM482:
    try:
        stored = receipt.to_verification()
    except IndependentM479VerificationReceiptM481PersistenceError as exc:
        raise IndependentM481VerificationReceiptM482Error(
            "persisted M4.81 verification receipt is structurally invalid"
        ) from exc

    if receipt.verification_receipt_id != source_receipt.id:
        raise IndependentM481VerificationReceiptM482Error(
            "M4.81 receipt source binding is invalid"
        )

    try:
        source_receipt.to_verification()
    except IndependentM477VerificationReceiptM479PersistenceError as exc:
        raise IndependentM481VerificationReceiptM482Error(
            "M4.79 source verification receipt is structurally invalid"
        ) from exc

    if source_receipt.snapshot_id != snapshot.id:
        raise IndependentM481VerificationReceiptM482Error(
            "M4.79 source receipt snapshot binding is invalid"
        )

    try:
        snapshot.to_integrity()
    except HistoricalM475VerificationReceiptHistoryIntegrityPersistenceError as exc:
        raise IndependentM481VerificationReceiptM482Error(
            "M4.77 source snapshot is structurally invalid"
        ) from exc

    try:
        reconstructed = independently_verify_m4_79_verification_receipt(
            receipt=source_receipt,
            snapshot=snapshot,
            source_records=source_records,
        )
    except (
        HistoricalM472VerificationReceiptM475PersistenceError,
        IndependentM477VerificationReceiptM480Error,
    ) as exc:
        raise IndependentM481VerificationReceiptM482Error(
            f"M4.80 independent reconstruction failed: {exc}"
        ) from exc

    blockers: list[str] = []
    if stored.verification_receipt_id != reconstructed.verification_receipt_id:
        blockers.append("M481_VERIFICATION_RECEIPT_ID_MISMATCH")
    if (
        stored.verification_fingerprint.lower()
        != reconstructed.verification_fingerprint.lower()
    ):
        blockers.append("M481_VERIFICATION_FINGERPRINT_MISMATCH")
    if (
        stored.persisted_fingerprint.lower()
        != reconstructed.persisted_fingerprint.lower()
    ):
        blockers.append("M481_PERSISTED_FINGERPRINT_MISMATCH")
    if (
        stored.reconstructed_fingerprint.lower()
        != reconstructed.reconstructed_fingerprint.lower()
    ):
        blockers.append("M481_RECONSTRUCTED_FINGERPRINT_MISMATCH")
    if stored.persisted_snapshot_id != reconstructed.persisted_snapshot_id:
        blockers.append("M481_PERSISTED_SNAPSHOT_ID_MISMATCH")
    if stored.reconstructed_snapshot_id != reconstructed.reconstructed_snapshot_id:
        blockers.append("M481_RECONSTRUCTED_SNAPSHOT_ID_MISMATCH")
    if stored.persisted_valid != reconstructed.valid:
        blockers.append("M481_PERSISTED_VALIDITY_MISMATCH")
    if stored.reconstructed_valid != reconstructed.reconstructed_valid:
        blockers.append("M481_RECONSTRUCTED_VALIDITY_MISMATCH")
    if stored.valid != reconstructed.valid:
        blockers.append("M481_VALIDITY_MISMATCH")

    blocker_tuple = tuple(blockers)
    valid = not blocker_tuple

    return IndependentM481VerificationReceiptM482(
        verification_receipt_id=stored.verification_receipt_id,
        persisted_fingerprint=stored.verification_fingerprint,
        reconstructed_fingerprint=reconstructed.verification_fingerprint,
        persisted_snapshot_id=stored.persisted_snapshot_id,
        reconstructed_snapshot_id=reconstructed.reconstructed_snapshot_id,
        persisted_valid=stored.valid,
        reconstructed_valid=reconstructed.valid,
        valid=valid,
        blockers=blocker_tuple,
        verification_fingerprint=_verification_fingerprint(
            verification_receipt_id=stored.verification_receipt_id,
            persisted_fingerprint=stored.verification_fingerprint,
            reconstructed_fingerprint=reconstructed.verification_fingerprint,
            persisted_snapshot_id=stored.persisted_snapshot_id,
            reconstructed_snapshot_id=reconstructed.reconstructed_snapshot_id,
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
