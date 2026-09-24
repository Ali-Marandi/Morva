from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from morva.persistence.independent_historical_freshness_receipt_verifications_m4_46 import (
    IndependentHistoricalFreshnessReceiptVerificationRecord,
)


class HistoricalFreshnessVerificationHistoryIntegrityError(ValueError):
    """Raised when an M4.47 history-integrity result is invalid."""


@dataclass(frozen=True, slots=True)
class HistoricalFreshnessVerificationHistoryIntegrity:
    integrity_version: int
    record_count: int
    valid_count: int
    chain_valid_count: int
    history_fingerprint: str
    fingerprint: str

    def __post_init__(self) -> None:
        if self.integrity_version != 1:
            raise HistoricalFreshnessVerificationHistoryIntegrityError(
                "unsupported historical verification history integrity version"
            )
        for name, value in (
            ("history_fingerprint", self.history_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise HistoricalFreshnessVerificationHistoryIntegrityError(
                    f"{name} must be SHA-256"
                )
        if self.record_count < 0:
            raise HistoricalFreshnessVerificationHistoryIntegrityError(
                "record_count cannot be negative"
            )
        if self.valid_count < 0 or self.valid_count > self.record_count:
            raise HistoricalFreshnessVerificationHistoryIntegrityError(
                "valid_count is outside record_count"
            )
        if self.chain_valid_count < 0 or self.chain_valid_count > self.record_count:
            raise HistoricalFreshnessVerificationHistoryIntegrityError(
                "chain_valid_count is outside record_count"
            )
        expected = _fingerprint(
            record_count=self.record_count,
            valid_count=self.valid_count,
            chain_valid_count=self.chain_valid_count,
            history_fingerprint=self.history_fingerprint,
        )
        if self.fingerprint.lower() != expected:
            raise HistoricalFreshnessVerificationHistoryIntegrityError(
                "history integrity fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "integrity_version": self.integrity_version,
            "record_count": self.record_count,
            "valid_count": self.valid_count,
            "chain_valid_count": self.chain_valid_count,
            "history_fingerprint": self.history_fingerprint.lower(),
            "fingerprint": self.fingerprint.lower(),
        }


def build_historical_freshness_verification_history_integrity(
    records: list[IndependentHistoricalFreshnessReceiptVerificationRecord],
) -> HistoricalFreshnessVerificationHistoryIntegrity:
    canonical_records: list[dict[str, object]] = []
    valid_count = 0
    chain_valid_count = 0

    ordered = sorted(
        records,
        key=lambda record: (
            _timestamp(record.created_at),
            str(record.id),
        ),
    )
    for record in ordered:
        verification = record.to_verification()
        if verification.valid:
            valid_count += 1
        if verification.chain_valid:
            chain_valid_count += 1
        canonical_records.append(
            {
                "id": str(record.id),
                "receipt_id": str(record.receipt_id),
                "lineage_id": str(record.lineage_id),
                "persisted_fingerprint": verification.persisted_fingerprint.lower(),
                "reconstructed_fingerprint": verification.reconstructed_fingerprint.lower(),
                "chain_valid": verification.chain_valid,
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
    return HistoricalFreshnessVerificationHistoryIntegrity(
        integrity_version=1,
        record_count=len(canonical_records),
        valid_count=valid_count,
        chain_valid_count=chain_valid_count,
        history_fingerprint=history_fingerprint,
        fingerprint=_fingerprint(
            record_count=len(canonical_records),
            valid_count=valid_count,
            chain_valid_count=chain_valid_count,
            history_fingerprint=history_fingerprint,
        ),
    )


def _timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _fingerprint(
    *,
    record_count: int,
    valid_count: int,
    chain_valid_count: int,
    history_fingerprint: str,
) -> str:
    payload = {
        "integrity_version": 1,
        "record_count": record_count,
        "valid_count": valid_count,
        "chain_valid_count": chain_valid_count,
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
