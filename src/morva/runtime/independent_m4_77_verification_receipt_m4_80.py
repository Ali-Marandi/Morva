from __future__ import annotations

from dataclasses import dataclass
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
from morva.persistence.independent_m4_77_verification_receipts_m4_79 import (
    IndependentM477VerificationReceiptM479PersistenceError,
    IndependentM477VerificationReceiptM479Record,
)
from morva.runtime.independent_historical_m4_75_verification_receipt_m4_78 import (
    IndependentHistoricalM475VerificationReceiptM478Error,
    independently_verify_historical_m4_75_verification_receipt_m4_77,
)


class IndependentM477VerificationReceiptM480Error(ValueError):
    """Raised when an M4.79 receipt fails independent M4.80 verification."""


@dataclass(frozen=True, slots=True)
class IndependentM477VerificationReceiptM480:
    verification_receipt_id: UUID
    source_verification_receipt_id: UUID
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
            source_verification_receipt_id=self.source_verification_receipt_id,
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
            "source_verification_receipt_id": str(
                self.source_verification_receipt_id
            ),
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
    source_receipt: IndependentHistoricalM475VerificationReceiptHistoryIntegrityRecord,
    snapshot: HistoricalM474VerificationReceiptHistoryIntegrityRecord,
    source_records: list[IndependentHistoricalM472VerificationHistoryIntegrityReceiptRecord],
    source_repository: IndependentHistoricalM472VerificationHistoryIntegrityReceiptRepository,
) -> IndependentM477VerificationReceiptM480:
    """Reconstruct M4.78 from source history, then compare it with the M4.79 row."""
    try:
        stored = receipt.to_verification()
    except IndependentM477VerificationReceiptM479PersistenceError as exc:
        raise IndependentM477VerificationReceiptM480Error(
            "persisted M4.79 verification receipt is structurally invalid"
        ) from exc

    if receipt.verification_receipt_id != source_receipt.id:
        raise IndependentM477VerificationReceiptM480Error(
            "M4.79 receipt source binding is invalid"
        )
    if source_receipt.snapshot_id != snapshot.id:
        raise IndependentM477VerificationReceiptM480Error(
            "M4.79 source receipt is bound to a different M4.75 snapshot"
        )

    try:
        source_receipt.to_verification()
    except IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError as exc:
        raise IndependentM477VerificationReceiptM480Error(
            "M4.77 source verification receipt is structurally invalid"
        ) from exc

    try:
        snapshot.to_integrity()
    except HistoricalM474VerificationReceiptHistoryIntegrityPersistenceError as exc:
        raise IndependentM477VerificationReceiptM480Error(
            "M4.75 source snapshot is structurally invalid"
        ) from exc

    try:
        reconstructed = independently_verify_historical_m4_75_verification_receipt_m4_77(
            receipt=source_receipt,
            snapshot=snapshot,
            source_records=source_records,
            source_repository=source_repository,
        )
    except (
        IndependentHistoricalM475VerificationReceiptHistoryIntegrityPersistenceError,
        IndependentHistoricalM472VerificationHistoryIntegrityReceiptPersistenceError,
        IndependentHistoricalM475VerificationReceiptM478Error,
    ) as exc:
        raise IndependentM477VerificationReceiptM480Error(
            f"M4.78 source reconstruction failed: {exc}"
        ) from exc

    comparisons = (
        (
            "M479_SOURCE_RECEIPT_ID_MISMATCH",
            stored.verification_receipt_id,
            reconstructed.verification_receipt_id,
        ),
        (
            "M479_PERSISTED_SNAPSHOT_ID_MISMATCH",
            stored.persisted_snapshot_id,
            reconstructed.persisted_snapshot_id,
        ),
        (
            "M479_RECONSTRUCTED_SNAPSHOT_ID_MISMATCH",
            stored.reconstructed_snapshot_id,
            reconstructed.reconstructed_snapshot_id,
        ),
        (
            "M479_PERSISTED_VERIFICATION_FINGERPRINT_MISMATCH",
            stored.persisted_verification_fingerprint.lower(),
            reconstructed.persisted_verification_fingerprint.lower(),
        ),
        (
            "M479_RECONSTRUCTED_VERIFICATION_FINGERPRINT_MISMATCH",
            stored.reconstructed_verification_fingerprint.lower(),
            reconstructed.reconstructed_verification_fingerprint.lower(),
        ),
        (
            "M479_PERSISTED_VALIDITY_MISMATCH",
            stored.persisted_valid,
            reconstructed.persisted_valid,
        ),
        (
            "M479_RECONSTRUCTED_VALIDITY_MISMATCH",
            stored.reconstructed_valid,
            reconstructed.reconstructed_valid,
        ),
        (
            "M479_PERSISTED_BLOCKERS_MISMATCH",
            stored.persisted_blockers,
            reconstructed.persisted_blockers,
        ),
        (
            "M479_RECONSTRUCTED_BLOCKERS_MISMATCH",
            stored.reconstructed_blockers,
            reconstructed.reconstructed_blockers,
        ),
        ("M479_VALIDITY_MISMATCH", stored.valid, reconstructed.valid),
        ("M479_BLOCKERS_MISMATCH", stored.blockers, reconstructed.blockers),
        (
            "M479_VERIFICATION_FINGERPRINT_MISMATCH",
            stored.verification_fingerprint.lower(),
            reconstructed.verification_fingerprint.lower(),
        ),
    )
    blockers = tuple(code for code, actual, expected in comparisons if actual != expected)
    return IndependentM477VerificationReceiptM480(
        verification_receipt_id=receipt.id,
        source_verification_receipt_id=source_receipt.id,
        persisted_fingerprint=stored.verification_fingerprint,
        reconstructed_fingerprint=reconstructed.verification_fingerprint,
        persisted_snapshot_id=stored.persisted_snapshot_id,
        reconstructed_snapshot_id=reconstructed.reconstructed_snapshot_id,
        persisted_valid=stored.valid,
        reconstructed_valid=reconstructed.valid,
        valid=not blockers,
        blockers=blockers,
        verification_fingerprint=_verification_fingerprint(
            verification_receipt_id=receipt.id,
            source_verification_receipt_id=source_receipt.id,
            persisted_fingerprint=stored.verification_fingerprint,
            reconstructed_fingerprint=reconstructed.verification_fingerprint,
            persisted_snapshot_id=stored.persisted_snapshot_id,
            reconstructed_snapshot_id=reconstructed.reconstructed_snapshot_id,
            persisted_valid=stored.valid,
            reconstructed_valid=reconstructed.valid,
            valid=not blockers,
            blockers=blockers,
        ),
    )


def _verification_fingerprint(
    *,
    verification_receipt_id: UUID,
    source_verification_receipt_id: UUID,
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
        "source_verification_receipt_id": str(source_verification_receipt_id),
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
