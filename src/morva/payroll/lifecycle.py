"""Canonical payroll lifecycle state machine.

This module is the single source of truth for payroll-run status and allowed
transitions. Legacy ``workflow.py`` imports are compatibility-only.
"""

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


_ALLOWED: dict[PayrollStatus, frozenset[PayrollStatus]] = {
    PayrollStatus.DRAFT: frozenset({PayrollStatus.DATA_RECEIVED, PayrollStatus.CANCELLED}),
    PayrollStatus.DATA_RECEIVED: frozenset({PayrollStatus.CALCULATING, PayrollStatus.CANCELLED}),
    PayrollStatus.CALCULATING: frozenset({PayrollStatus.VALIDATING, PayrollStatus.DRAFT, PayrollStatus.CANCELLED}),
    PayrollStatus.VALIDATING: frozenset({PayrollStatus.REVIEWED, PayrollStatus.CALCULATING, PayrollStatus.CANCELLED}),
    PayrollStatus.REVIEWED: frozenset({PayrollStatus.APPROVED, PayrollStatus.CANCELLED}),
    PayrollStatus.APPROVED: frozenset({PayrollStatus.FROZEN, PayrollStatus.CANCELLED}),
    PayrollStatus.FROZEN: frozenset({PayrollStatus.EXPORTED, PayrollStatus.CANCELLED}),
    PayrollStatus.EXPORTED: frozenset({PayrollStatus.SUBMITTED, PayrollStatus.CANCELLED}),
    PayrollStatus.SUBMITTED: frozenset({PayrollStatus.PAYMENT_CONFIRMED, PayrollStatus.CANCELLED}),
    PayrollStatus.PAYMENT_CONFIRMED: frozenset({PayrollStatus.RECONCILED}),
    PayrollStatus.RECONCILED: frozenset(),
    PayrollStatus.CANCELLED: frozenset(),
}


def can_transition(current: PayrollStatus, target: PayrollStatus) -> bool:
    return target in _ALLOWED[current]


def transition(current: PayrollStatus, target: PayrollStatus) -> PayrollStatus:
    if not can_transition(current, target):
        raise ValueError(f"invalid payroll transition: {current} -> {target}")
    return target
