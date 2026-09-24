from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from uuid import UUID

from morva.persistence.historical_freshness_chain_verification_receipts_m4_44 import (
    HistoricalFreshnessChainVerificationReceiptRecord,
    HistoricalFreshnessChainVerificationReceiptPersistenceError,
)
from morva.runtime.historical_freshness_chain_verifier_m4_43 import (
    HistoricalFreshnessChainVerification,
    HistoricalFreshnessChainVerificationError,
)
from morva.runtime.historical_freshness_chain_verifier_m4_43 import (
    verify_historical_freshness_chain,
)


class IndependentHistoricalFreshnessChainVerificationReceiptError(ValueError):
    """Raised when an M4.44 receipt fails independent verification."""


@dataclass(frozen=True, slots=True)
class IndependentHistoricalFreshnessChainVerificationReceipt:
    receipt_id: UUID
    lineage_id: UUID
    persisted_fingerprint: str
    reconstructed_fingerprint: str
    chain_valid: bool
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
                raise IndependentHistoricalFreshnessChainVerificationReceiptError(
                    f"{name} must be SHA-256"
                )
        expected = _fingerprint(
            receipt_id=self.receipt_id,
            lineage_id=self.lineage_id,
            persisted_fingerprint=self.persisted_fingerprint,
            reconstructed_fingerprint=self.reconstructed_fingerprint,
            chain_valid=self.chain_valid,
            valid=self.valid,
            blockers=self.blockers,
        )
        if self.verification_fingerprint.lower() != expected:
            raise IndependentHistoricalFreshnessChainVerificationReceiptError(
                "independent M4.44 receipt verification fingerprint mismatch"
            )

    def to_payload(self) -> dict[str, object]:
        return {
            "receipt_id": str(self.receipt_id),
            "lineage_id": str(self.lineage_id),
            "persisted_fingerprint": self.persisted_fingerprint.lower(),
            "reconstructed_fingerprint": self.reconstructed_fingerprint.lower(),
            "chain_valid": self.chain_valid,
            "valid": self.valid,
            "blockers": list(self.blockers),
            "verification_fingerprint": self.verification_fingerprint.lower(),
        }


def verify_historical_freshness_chain_verification_receipt(
    *,
    receipt: HistoricalFreshnessChainVerificationReceiptRecord,
    reconstructed: HistoricalFreshnessChainVerification,
) -> IndependentHistoricalFreshnessChainVerificationReceipt:
    try:
        persisted = receipt.to_verification()
    except HistoricalFreshnessChainVerificationReceiptPersistenceError as exc:
        raise IndependentHistoricalFreshnessChainVerificationReceiptError(
            "persisted M4.44 receipt is structurally invalid"
        ) from exc

    same_identity = persisted.freshness_receipt_id == reconstructed.freshness_receipt_id
    same_identity = same_identity and persisted.historical_binding_id == reconstructed.historical_binding_id
    same_identity = same_identity and persisted.snapshot_id == reconstructed.snapshot_id
    same_identity = same_identity and persisted.lineage_fingerprint == reconstructed.lineage_fingerprint
    same_identity = same_identity and persisted.freshness_receipt_fingerprint == reconstructed.freshness_receipt_fingerprint
    same_identity = same_identity and persisted.historical_binding_fingerprint == reconstructed.historical_binding_fingerprint
    same_identity = same_identity and persisted.snapshot_fingerprint == reconstructed.snapshot_fingerprint
    same_identity = same_identity and persisted.policy_id == reconstructed.policy_id
    same_identity = same_identity and persisted.policy_version == reconstructed.policy_version
    same_identity = same_identity and persisted.policy_fingerprint == reconstructed.policy_fingerprint
    same_identity = same_identity and persisted.registry_integrity_version == reconstructed.registry_integrity_version
    same_identity = same_identity and persisted.registry_policy_count == reconstructed.registry_policy_count
    same_identity = same_identity and persisted.registry_fingerprint == reconstructed.registry_fingerprint
    same_identity = same_identity and persisted.state == reconstructed.state
    same_identity = same_identity and persisted.blockers == reconstructed.blockers
    same_identity = same_identity and persisted.fingerprint == reconstructed.fingerprint

    blockers = () if same_identity else ("PERSISTED_RECEIPT_CHAIN_MISMATCH",)
    valid = same_identity
    return IndependentHistoricalFreshnessChainVerificationReceipt(
        receipt_id=receipt.id,
        lineage_id=receipt.lineage_id,
        persisted_fingerprint=persisted.fingerprint,
        reconstructed_fingerprint=reconstructed.fingerprint,
        chain_valid=reconstructed.valid,
        valid=valid,
        blockers=blockers,
        verification_fingerprint=_fingerprint(
            receipt_id=receipt.id,
            lineage_id=receipt.lineage_id,
            persisted_fingerprint=persisted.fingerprint,
            reconstructed_fingerprint=reconstructed.fingerprint,
            chain_valid=reconstructed.valid,
            valid=valid,
            blockers=blockers,
        ),
    )


def _fingerprint(
    *,
    receipt_id: UUID,
    lineage_id: UUID,
    persisted_fingerprint: str,
    reconstructed_fingerprint: str,
    chain_valid: bool,
    valid: bool,
    blockers: tuple[str, ...],
) -> str:
    payload = {
        "verification_version": 1,
        "receipt_id": str(receipt_id),
        "lineage_id": str(lineage_id),
        "persisted_fingerprint": persisted_fingerprint.lower(),
        "reconstructed_fingerprint": reconstructed_fingerprint.lower(),
        "chain_valid": chain_valid,
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
