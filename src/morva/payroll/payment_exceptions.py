"""Fail-closed payment exception lifecycle for M3.28.

This module intentionally models provider-neutral exception states only. It does
not encode bank/Treasury contracts, statutory amounts, or retry semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PaymentExceptionType(str, Enum):
    RETURN = "return"
    REJECT = "reject"
    PARTIAL_SETTLEMENT = "partial_settlement"
    REVERSAL = "reversal"
    UNRESOLVED_MISMATCH = "unresolved_mismatch"


class PaymentExceptionStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class PaymentException:
    exception_id: str
    payment_item_id: str
    exception_type: PaymentExceptionType
    reason: str
    status: PaymentExceptionStatus = PaymentExceptionStatus.OPEN
    resolution_actor: str | None = None
    resolution_reason: str | None = None
    evidence_ref: str | None = None

    def resolve(self, *, actor: str, reason: str, evidence_ref: str) -> "PaymentException":
        """Resolve an exception only with explicit actor, reason and evidence."""
        if self.status is not PaymentExceptionStatus.OPEN:
            raise ValueError("only open payment exceptions can be resolved")
        if not actor.strip() or not reason.strip() or not evidence_ref.strip():
            raise ValueError("resolution actor, reason and evidence are required")
        return PaymentException(
            exception_id=self.exception_id,
            payment_item_id=self.payment_item_id,
            exception_type=self.exception_type,
            reason=self.reason,
            status=PaymentExceptionStatus.RESOLVED,
            resolution_actor=actor,
            resolution_reason=reason,
            evidence_ref=evidence_ref,
        )


def release_is_allowed(exceptions: list[PaymentException]) -> bool:
    """Return whether external payment release may proceed.

    Any missing/unknown/blocked/unresolved exception fails closed.
    """
    return all(exception.status is PaymentExceptionStatus.RESOLVED for exception in exceptions)
