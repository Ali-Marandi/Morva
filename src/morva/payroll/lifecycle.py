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
    CANCELLED = "cancelled"


_ALLOWED: dict[PayrollStatus, set[PayrollStatus]] = {
    PayrollStatus.DRAFT: {PayrollStatus.CALCULATING, PayrollStatus.CANCELLED},
    PayrollStatus.CALCULATING: {PayrollStatus.VALIDATING, PayrollStatus.DRAFT, PayrollStatus.CANCELLED},
    PayrollStatus.VALIDATING: {PayrollStatus.APPROVED, PayrollStatus.CALCULATING, PayrollStatus.CANCELLED},
    PayrollStatus.APPROVED: {PayrollStatus.FROZEN, PayrollStatus.CANCELLED},
    PayrollStatus.FROZEN: {PayrollStatus.EXPORTED, PayrollStatus.CANCELLED},
    PayrollStatus.EXPORTED: {PayrollStatus.PAID},
    PayrollStatus.PAID: set(),
    PayrollStatus.CANCELLED: set(),
}


def transition(current: PayrollStatus, target: PayrollStatus) -> PayrollStatus:
    if target not in _ALLOWED[current]:
        raise ValueError(f"invalid payroll transition: {current} -> {target}")
    return target
