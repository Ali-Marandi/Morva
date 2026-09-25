from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.persistence.independent_historical_m4_56_receipt_verification_persistence_m4_57 import (
    IndependentHistoricalM455ReceiptVerificationRecord,
)


class HistoricalM457VerificationReceiptHistoryIntegrityError(ValueError):
    """Raised when an M4.58 M4.57 receipt-history integrity result is invalid."""


@dataclass(frozen=True, slots=True)
class HistoricalM457VerificationReceiptHistoryIntegrity:
    integrity_version: int
    record_count: int
    valid_count: int
    history_fingerprint: str
    fingerprint: str

    def __post_init__(self) -> None:
        if self.integrity_version != 1:
            raise HistoricalM457VerificationReceiptHistoryIntegrityError(
                "unsupported M4.58 receipt-history integrity version"
            )
        for name, value in (("history_fingerprint", self.history_fingerprint), ("fingerprint", self.fingerprint)):
            if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
                raise HistoricalM457VerificationReceiptHistoryIntegrityError(f"{name} must be SHA-256")
        if self.record_count < 0:
            raise HistoricalM457VerificationReceiptHistoryIntegrityError("record_count cannot be negative")
        if self.valid_count < 0 or self.valid_count > self.record_count:
            raise HistoricalM457VerificationReceiptHistoryIntegrityError("valid_count is outside record_count")
        expected = _fingerprint(
            record_count=self.record_count,
            valid_count=self.valid_count,
            history_fingerprint=self.history_fingerprint,
        )
        if self.fingerprint.lower() != expected:
            raise HistoricalM457VerificationReceiptHistoryIntegrityError(
                "M4.58 receipt-history integrity fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "integrity_version": self.integrity_version,
            "record_count": self.record_count,
            "valid_count": self.valid_count,
            "history_fingerprint": self.history_fingerprint.lower(),
            "fingerprint": self.fingerprint.lower(),
        }


def build_historical_m4_57_verification_receipt_history_integrity(
    records: list[IndependentHistoricalM455ReceiptVerificationRecord],
) -> HistoricalM457VerificationReceiptHistoryIntegrity:
    canonical_records: list[dict[str, object]] = []
    valid_count = 0
    ordered = sorted(records, key=lambda record: (_timestamp(record.created_at), str(record.id)))
    for record in ordered:
        verification = record.to_verification()
        if verification.valid:
            valid_count += 1
        canonical_records.append(
            {
                "id": str(record.id),
                "receipt_id": str(record.receipt_id),
                "persisted_snapshot_id": str(record.persisted_snapshot_id),
                "reconstructed_snapshot_id": str(record.reconstructed_snapshot_id),
                "persisted_verification_fingerprint": verification.persisted_verification_fingerprint.lower(),
                "reconstructed_verification_fingerprint": verification.reconstructed_verification_fingerprint.lower(),
                "valid": verification.valid,
                "blockers": list(verification.blockers),
                "verification_fingerprint": verification.verification_fingerprint.lower(),
                "recorded_by": record.recorded_by,
                "created_at": _timestamp(record.created_at),
            }
        )
    history_fingerprint = sha256(
        json.dumps(canonical_records, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    count = len(canonical_records)
    return HistoricalM457VerificationReceiptHistoryIntegrity(
        integrity_version=1,
        record_count=count,
        valid_count=valid_count,
        history_fingerprint=history_fingerprint,
        fingerprint=_fingerprint(
            record_count=count, valid_count=valid_count, history_fingerprint=history_fingerprint
        ),
    )


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _fingerprint(*, record_count: int, valid_count: int, history_fingerprint: str) -> str:
    payload = {
        "integrity_version": 1,
        "record_count": record_count,
        "valid_count": valid_count,
        "history_fingerprint": history_fingerprint.lower(),
    }
    return sha256(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()