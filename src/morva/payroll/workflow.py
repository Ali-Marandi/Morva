from __future__ import annotations

from enum import StrEnum


class PayrollStatus(StrEnum):
    DRAFT = "draft"
    CALCULATING = "calculating"
    VALIDATING = "validating"
    APPROVED = "approved"
    FROZEN = "frozen"
    EXPORTED = "exported"
    PAID = "paid"
    REJECTED = "rejected"


_ALLOWED: dict[PayrollStatus, set[PayrollStatus]] = {
    PayrollStatus.DRAFT: {PayrollStatus.CALCULATING, PayrollStatus.REJECTED},
    PayrollStatus.CALCULATING: {PayrollStatus.VALIDATING, PayrollStatus.REJECTED},
    PayrollStatus.VALIDATING: {PayrollStatus.APPROVED, PayrollStatus.REJECTED},
    PayrollStatus.APPROVED: {PayrollStatus.FROZEN, PayrollStatus.REJECTED},
    PayrollStatus.FROZEN: {PayrollStatus.EXPORTED},
    PayrollStatus.EXPORTED: {PayrollStatus.PAID},
    PayrollStatus.PAID: set(),
    PayrollStatus.REJECTED: {PayrollStatus.DRAFT},
}


def can_transition(current: PayrollStatus, target: PayrollStatus) -> bool:
    return target in _ALLOWED[current]


def transition(current: PayrollStatus, target: PayrollStatus) -> PayrollStatus:
    if not can_transition(current, target):
        raise ValueError(f"invalid payroll transition: {current} -> {target}")
    return target
