from __future__ import annotations

from enum import StrEnum


class PayrollStatus(StrEnum):
    DRAFT = "draft"
    DATA_RECEIVED = "data_received"
    CALCULATING = "calculating"
    VALIDATING = "validating"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    FROZEN = "frozen"
    EXPORTED = "exported"
    SUBMITTED = "submitted"
    PAYMENT_CONFIRMED = "payment_confirmed"
    RECONCILED = "reconciled"
    CANCELLED = "cancelled"


_ALLOWED: dict[PayrollStatus, set[PayrollStatus]] = {
    PayrollStatus.DRAFT: {PayrollStatus.DATA_RECEIVED, PayrollStatus.CANCELLED},
    PayrollStatus.DATA_RECEIVED: {PayrollStatus.CALCULATING, PayrollStatus.CANCELLED},
    PayrollStatus.CALCULATING: {PayrollStatus.VALIDATING, PayrollStatus.DRAFT, PayrollStatus.CANCELLED},
    PayrollStatus.VALIDATING: {PayrollStatus.REVIEWED, PayrollStatus.CALCULATING, PayrollStatus.CANCELLED},
    PayrollStatus.REVIEWED: {PayrollStatus.APPROVED, PayrollStatus.CANCELLED},
    PayrollStatus.APPROVED: {PayrollStatus.FROZEN, PayrollStatus.CANCELLED},
    PayrollStatus.FROZEN: {PayrollStatus.EXPORTED, PayrollStatus.CANCELLED},
    PayrollStatus.EXPORTED: {PayrollStatus.SUBMITTED, PayrollStatus.CANCELLED},
    PayrollStatus.SUBMITTED: {PayrollStatus.PAYMENT_CONFIRMED, PayrollStatus.CANCELLED},
    PayrollStatus.PAYMENT_CONFIRMED: {PayrollStatus.RECONCILED},
    PayrollStatus.RECONCILED: set(),
    PayrollStatus.CANCELLED: set(),
}


def transition(current: PayrollStatus, target: PayrollStatus) -> PayrollStatus:
    if target not in _ALLOWED[current]:
        raise ValueError(f"invalid payroll transition: {current} -> {target}")
    return target
