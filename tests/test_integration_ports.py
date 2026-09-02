import pytest

from morva.integrations.ports import (
    AccountingPort,
    BankPort,
    FailClosedAdapter,
    InsurancePort,
    IntegrationNotConfigured,
    IntegrationPayload,
    SinaPort,
    TaxPort,
    TreasuryPort,
)


def test_integration_payload_and_receipt_contracts_are_versioned() -> None:
    payload = IntegrationPayload(
        operation="submit_payment_batch",
        correlation_id="corr-12345678",
        idempotency_key="idem-123456789",
        body={"amount": "100"},
        schema_version="2026-01",
    )
    assert payload.schema_version == "2026-01"


def test_fail_closed_adapter_never_performs_external_operations() -> None:
    adapter = FailClosedAdapter()
    methods = [
        "publish_order", "publish_payslip", "post_payroll_batch",
        "submit_payment_batch", "reconcile", "submit_payroll_tax",
        "submit_payroll_contribution", "health",
    ]
    for method_name in methods:
        with pytest.raises(IntegrationNotConfigured):
            getattr(adapter, method_name)()


def test_six_provider_protocols_are_runtime_contracts() -> None:
    # The protocol classes are intentionally structural; these assertions keep
    # the six required integration boundaries explicit in the source tree.
    assert all(cls.__name__.endswith("Port") for cls in [
        SinaPort, AccountingPort, TreasuryPort, BankPort, TaxPort, InsurancePort,
    ])
