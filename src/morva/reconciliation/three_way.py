from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256


@dataclass(frozen=True, slots=True)
class ThreeWayReconciliationRequest:
    artifact_id: str
    period: str
    currency: str
    entitlement_ref: str
    entitlement_fingerprint: str
    entitlement_amount: Decimal
    treasury_ref: str
    treasury_fingerprint: str
    treasury_amount: Decimal
    bank_ref: str
    bank_fingerprint: str
    bank_amount: Decimal
    reconciled_at: datetime
    reviewer_id: str
    approver_id: str
    status: str = "review_required"

    def validate(self) -> None:
        required = (
            ("artifact_id", self.artifact_id),
            ("period", self.period),
            ("currency", self.currency),
            ("entitlement_ref", self.entitlement_ref),
            ("entitlement_fingerprint", self.entitlement_fingerprint),
            ("treasury_ref", self.treasury_ref),
            ("treasury_fingerprint", self.treasury_fingerprint),
            ("bank_ref", self.bank_ref),
            ("bank_fingerprint", self.bank_fingerprint),
            ("reviewer_id", self.reviewer_id),
            ("approver_id", self.approver_id),
        )
        for name, value in required:
            if not value.strip():
                raise ValueError(f"{name} is required")
        for name, value in (
            ("entitlement_fingerprint", self.entitlement_fingerprint),
            ("treasury_fingerprint", self.treasury_fingerprint),
            ("bank_fingerprint", self.bank_fingerprint),
        ):
            if len(value) != 64 or any(c not in "0123456789abcdefABCDEF" for c in value):
                raise ValueError(f"{name} must be a 64-character SHA-256 hex digest")
        for name, amount in (
            ("entitlement_amount", self.entitlement_amount),
            ("treasury_amount", self.treasury_amount),
            ("bank_amount", self.bank_amount),
        ):
            if not isinstance(amount, Decimal) or not amount.is_finite() or amount < 0:
                raise ValueError(f"{name} must be a finite non-negative Decimal")
        if self.reconciled_at.tzinfo is None:
            raise ValueError("reconciled_at must be timezone-aware")
        if self.reviewer_id.strip() == self.approver_id.strip():
            raise ValueError("reviewer and approver must be distinct")
        if self.status not in {"review_required", "reconciled"}:
            raise ValueError("status must be review_required or reconciled")

    def execution_ready(self) -> bool:
        try:
            self.validate()
        except ValueError:
            return False
        refs_match = len({self.entitlement_ref.strip(), self.treasury_ref.strip(), self.bank_ref.strip()}) == 3
        fingerprints_match = len({self.entitlement_fingerprint.lower(), self.treasury_fingerprint.lower(), self.bank_fingerprint.lower()}) == 1
        amounts_match = self.entitlement_amount == self.treasury_amount == self.bank_amount
        return self.status == "reconciled" and refs_match and fingerprints_match and amounts_match

    def reconciliation_fingerprint(self) -> str:
        self.validate()
        canonical = "|".join(
            (
                self.artifact_id.strip(),
                self.period.strip(),
                self.currency.strip().upper(),
                self.entitlement_ref.strip(),
                self.entitlement_fingerprint.lower(),
                str(self.entitlement_amount),
                self.treasury_ref.strip(),
                self.treasury_fingerprint.lower(),
                str(self.treasury_amount),
                self.bank_ref.strip(),
                self.bank_fingerprint.lower(),
                str(self.bank_amount),
                self.reconciled_at.isoformat(),
                self.reviewer_id.strip(),
                self.approver_id.strip(),
                self.status,
            )
        )
        return sha256(canonical.encode("utf-8")).hexdigest()
