from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class IntegrationPayload:
    operation: str
    correlation_id: str
    idempotency_key: str
    body: dict[str, object]


@dataclass(frozen=True, slots=True)
class IntegrationReceipt:
    provider: str
    external_id: str
    correlation_id: str


class SinaPort(Protocol):
    def publish_order(self, payload: IntegrationPayload) -> IntegrationReceipt: ...
    def publish_payslip(self, payload: IntegrationPayload) -> IntegrationReceipt: ...
    def health(self) -> bool: ...


class AccountingPort(Protocol):
    def post_payroll_batch(self, payload: IntegrationPayload) -> IntegrationReceipt: ...
    def health(self) -> bool: ...


class TreasuryPort(Protocol):
    def submit_payment_batch(self, payload: IntegrationPayload) -> IntegrationReceipt: ...
    def health(self) -> bool: ...


class BankPort(Protocol):
    def submit_payment_batch(self, payload: IntegrationPayload) -> IntegrationReceipt: ...
    def reconcile(self, payload: IntegrationPayload) -> IntegrationReceipt: ...
    def health(self) -> bool: ...


class IntegrationNotConfigured(RuntimeError):
    pass


class FailClosedAdapter:
    """Default adapter: no payment/export occurs until an approved integration is configured."""

    def __getattr__(self, name: str):
        def _missing(*_args, **_kwargs):
            raise IntegrationNotConfigured(f"external integration is not configured: {name}")
        return _missing
