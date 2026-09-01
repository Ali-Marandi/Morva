from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class PayslipLineView:
    code: str
    title: str
    amount: Decimal
    kind: str
    explanation: str
    legal_reference: str | None = None


@dataclass(frozen=True, slots=True)
class PayslipView:
    employee_no: str
    period: str
    gross: Decimal
    deductions: Decimal
    net: Decimal
    lines: tuple[PayslipLineView, ...]
    fingerprint: str


@dataclass(frozen=True, slots=True)
class Objection:
    objection_id: str
    employee_no: str
    subject: str
    description: str
    status: str = "submitted"
