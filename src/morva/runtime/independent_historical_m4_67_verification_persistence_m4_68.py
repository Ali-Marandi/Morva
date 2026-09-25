from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from morva.runtime.independent_historical_m4_66_receipt_verifier_m4_67 import (
    IndependentHistoricalM466ReceiptVerificationError,
    independently_verify_historical_m4_66_receipt,
)
from morva.persistence.historical_m4_63_receipt_history_integrity_m4_64 import (
    HistoricalM463ReceiptHistoryIntegrityRecord,
)
from morva.persistence.independent_historical_m4_61_receipt_history_verification_m4_63 import (
    IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord,
)
from morva.persistence.independent_historical_m4_64_verification_receipts_m4_66 import (
    IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord,
)


class IndependentHistoricalM466VerificationPersistenceError(ValueError):
    """Raised when an M4.68 persisted M4.67 result is invalid."""


@dataclass(frozen=True, slots=True)
class IndependentHistoricalM466VerificationPersistenceReceipt:
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
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise IndependentHistoricalM466VerificationPersistenceError(
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
            raise IndependentHistoricalM466VerificationPersistenceError(
                "M4.68 verification fingerprint mismatch"
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


def persist_historical_m4_67_verification(
    *,
    receipt: IndependentHistoricalM464ReceiptHistoryIntegrityReceiptRecord,
    snapshot: HistoricalM463ReceiptHistoryIntegrityRecord,
    source_records: list[IndependentHistoricalM461ReceiptHistoryIntegrityReceiptRecord],
) -> IndependentHistoricalM466VerificationPersistenceReceipt:
    try:
        reconstructed = independently_verify_historical_m4_66_receipt(
            receipt=receipt,
            snapshot=snapshot,
            source_records=source_records,
        )
    except IndependentHistoricalM466ReceiptVerificationError as exc:
        raise IndependentHistoricalM466VerificationPersistenceError(
            "M4.67 independent reconstruction failed"
        ) from exc

    return IndependentHistoricalM466VerificationPersistenceReceipt(
        verification_receipt_id=receipt.id,
        persisted_snapshot_id=reconstructed.persisted_snapshot_id,
        reconstructed_snapshot_id=reconstructed.reconstructed_snapshot_id,
        persisted_verification_fingerprint=reconstructed.persisted_verification_fingerprint,
        reconstructed_verification_fingerprint=reconstructed.reconstructed_verification_fingerprint,
        valid=reconstructed.valid,
        blockers=reconstructed.blockers,
        verification_fingerprint=_verification_fingerprint(
            verification_receipt_id=receipt.id,
            persisted_snapshot_id=reconstructed.persisted_snapshot_id,
            reconstructed_snapshot_id=reconstructed.reconstructed_snapshot_id,
            persisted_verification_fingerprint=reconstructed.persisted_verification_fingerprint,
            reconstructed_verification_fingerprint=reconstructed.reconstructed_verification_fingerprint,
            valid=reconstructed.valid,
            blockers=reconstructed.blockers,
        ),
    )


def _verification_fingerprint(
    *,
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
        "receipt_id": str(verification_receipt_id),
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
