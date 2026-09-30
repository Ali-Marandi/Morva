from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from uuid import UUID

from morva.persistence.historical_m4_72_verification_receipt_m4_75 import (
    HistoricalM472VerificationReceiptM475PersistenceError,
    HistoricalM472VerificationReceiptM475Record,
)


class HistoricalM475VerificationReceiptHistoryIntegrityError(ValueError):
    """Raised when an M4.77 history-integrity snapshot is invalid or tampered."""


@dataclass(frozen=True, slots=True)
class HistoricalM475VerificationReceiptHistoryIntegrity:
    integrity_version: int
    record_count: int
    valid_count: int
    history_fingerprint: str
    fingerprint: str

    def __post_init__(self) -> None:
        if self.integrity_version != 1:
            raise HistoricalM475VerificationReceiptHistoryIntegrityError(
                "unsupported M4.77 integrity version"
            )
        if self.record_count < 0 or self.valid_count < 0:
            raise HistoricalM475VerificationReceiptHistoryIntegrityError(
                "record_count and valid_count cannot be negative"
            )
        if self.valid_count > self.record_count:
            raise HistoricalM475VerificationReceiptHistoryIntegrityError(
                "valid_count cannot exceed record_count"
            )
        for name, value in (
            ("history_fingerprint", self.history_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise HistoricalM475VerificationReceiptHistoryIntegrityError(
                    f"{name} must be SHA-256"
                )

        expected = _snapshot_fingerprint(
            integrity_version=self.integrity_version,
            record_count=self.record_count,
            valid_count=self.valid_count,
            history_fingerprint=self.history_fingerprint,
        )
        if self.fingerprint.lower() != expected:
            raise HistoricalM475VerificationReceiptHistoryIntegrityError(
                "M4.77 integrity fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "integrity_version": self.integrity_version,
            "record_count": self.record_count,
            "valid_count": self.valid_count,
            "history_fingerprint": self.history_fingerprint.lower(),
            "fingerprint": self.fingerprint.lower(),
        }


def build_historical_m4_75_verification_receipt_history_integrity(
    records: list[HistoricalM472VerificationReceiptM475Record],
) -> HistoricalM475VerificationReceiptHistoryIntegrity:
    ordered = sorted(
        records,
        key=lambda record: (_timestamp(record.created_at), str(record.id)),
    )
    canonical_records: list[dict[str, object]] = []
    valid_count = 0

    for record in ordered:
        try:
            verification = record.to_verification()
        except HistoricalM472VerificationReceiptM475PersistenceError as exc:
            raise HistoricalM475VerificationReceiptHistoryIntegrityError(
                "M4.76 source verification result is structurally invalid"
            ) from exc

        if verification.valid:
            valid_count += 1

        canonical_records.append(
            {
                "id": str(record.id),
                "verification_receipt_id": str(record.verification_receipt_id),
                "persisted_fingerprint": verification.persisted_fingerprint.lower(),
                "reconstructed_fingerprint": verification.reconstructed_fingerprint.lower(),
                "persisted_snapshot_id": str(verification.persisted_snapshot_id),
                "reconstructed_snapshot_id": str(
                    verification.reconstructed_snapshot_id
                ),
                "persisted_valid": verification.persisted_valid,
                "reconstructed_valid": verification.reconstructed_valid,
                "valid": verification.valid,
                "blockers": list(verification.blockers),
                "verification_fingerprint": verification.verification_fingerprint.lower(),
                "recorded_by": record.recorded_by,
                "created_at": _timestamp(record.created_at),
            }
        )

    history_fingerprint = _canonical_sha256(canonical_records)
    record_count = len(canonical_records)

    return HistoricalM475VerificationReceiptHistoryIntegrity(
        integrity_version=1,
        record_count=record_count,
        valid_count=valid_count,
        history_fingerprint=history_fingerprint,
        fingerprint=_snapshot_fingerprint(
            integrity_version=1,
            record_count=record_count,
            valid_count=valid_count,
            history_fingerprint=history_fingerprint,
        ),
    )


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _canonical_sha256(payload: object) -> str:
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _snapshot_fingerprint(
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
    return _canonical_sha256(payload)
