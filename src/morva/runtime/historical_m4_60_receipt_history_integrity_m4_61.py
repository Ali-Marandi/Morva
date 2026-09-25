from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.persistence.independent_historical_m4_58_receipt_history_verification_m4_60 import (
    IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord,
)


class HistoricalM460ReceiptHistoryIntegrityError(ValueError):
    """Raised when an M4.61 M4.60 receipt-history integrity result is invalid."""


@dataclass(frozen=True, slots=True)
class HistoricalM460ReceiptHistoryIntegrity:
    integrity_version: int
    record_count: int
    valid_count: int
    history_fingerprint: str
    fingerprint: str

    def __post_init__(self) -> None:
        if self.integrity_version != 1:
            raise HistoricalM460ReceiptHistoryIntegrityError(
                "unsupported M4.61 receipt-history integrity version"
            )
        for name, value in (
            ("history_fingerprint", self.history_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise HistoricalM460ReceiptHistoryIntegrityError(
                    f"{name} must be SHA-256"
                )
        if self.record_count < 0:
            raise HistoricalM460ReceiptHistoryIntegrityError(
                "record_count cannot be negative"
            )
        if self.valid_count < 0 or self.valid_count > self.record_count:
            raise HistoricalM460ReceiptHistoryIntegrityError(
                "valid_count is outside record_count"
            )
        expected = _fingerprint(
            record_count=self.record_count,
            valid_count=self.valid_count,
            history_fingerprint=self.history_fingerprint,
        )
        if self.fingerprint.lower() != expected:
            raise HistoricalM460ReceiptHistoryIntegrityError(
                "M4.61 receipt-history integrity fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "integrity_version": self.integrity_version,
            "record_count": self.record_count,
            "valid_count": self.valid_count,
            "history_fingerprint": self.history_fingerprint.lower(),
            "fingerprint": self.fingerprint.lower(),
        }


def build_historical_m4_60_receipt_history_integrity(
    records: list[IndependentHistoricalM458ReceiptHistoryIntegrityReceiptRecord],
) -> HistoricalM460ReceiptHistoryIntegrity:
    canonical_records: list[dict[str, object]] = []
    valid_count = 0

    for record in sorted(
        records,
        key=lambda item: (_timestamp(item.created_at), str(item.id)),
    ):
        verification = record.to_verification()
        if verification.valid:
            valid_count += 1
        canonical_records.append(
            {
                "id": str(record.id),
                "snapshot_id": str(record.snapshot_id),
                "persisted_fingerprint": verification.persisted_fingerprint.lower(),
                "reconstructed_fingerprint": verification.reconstructed_fingerprint.lower(),
                "persisted_history_fingerprint": verification.persisted_history_fingerprint.lower(),
                "reconstructed_history_fingerprint": verification.reconstructed_history_fingerprint.lower(),
                "persisted_record_count": verification.persisted_record_count,
                "reconstructed_record_count": verification.reconstructed_record_count,
                "persisted_valid_count": verification.persisted_valid_count,
                "reconstructed_valid_count": verification.reconstructed_valid_count,
                "valid": verification.valid,
                "blockers": list(verification.blockers),
                "verification_fingerprint": verification.verification_fingerprint.lower(),
                "recorded_by": record.recorded_by,
                "created_at": _timestamp(record.created_at),
            }
        )

    history_fingerprint = sha256(
        json.dumps(
            canonical_records,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    count = len(canonical_records)
    return HistoricalM460ReceiptHistoryIntegrity(
        integrity_version=1,
        record_count=count,
        valid_count=valid_count,
        history_fingerprint=history_fingerprint,
        fingerprint=_fingerprint(
            record_count=count,
            valid_count=valid_count,
            history_fingerprint=history_fingerprint,
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
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
