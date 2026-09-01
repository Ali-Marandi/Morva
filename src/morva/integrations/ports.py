from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class IntegrationPayload:
    operation: str
    correlation_id: str
    body: dict[str, object]


class SinaPort(Protocol):
    def publish_order(self, payload: IntegrationPayload) -> None: ...
    def publish_payslip(self, payload: IntegrationPayload) -> None: ...
    def health(self) -> bool: ...


class AccountingPort(Protocol):
    def post_payroll_batch(self, payload: IntegrationPayload) -> None: ...
    def health(self) -> bool: ...


class TreasuryPort(Protocol):
    def submit_payment_batch(self, payload: IntegrationPayload) -> None: ...
    def health(self) -> bool: ...


class BankPort(Protocol):
    def reconcile(self, payload: IntegrationPayload) -> None: ...
    def health(self) -> bool: ...
