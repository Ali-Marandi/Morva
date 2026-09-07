from decimal import Decimal

import pytest

from morva.integrations.payroll_contract import IntegrationContractError, PayrollTransfer, assert_same_batch


def transfer(*, batch_id: str = "BATCH-1", correlation_id: str = "CORR-1", net: str = "97200000") -> PayrollTransfer:
    return PayrollTransfer(
        system="synthetic-finance",
        batch_id=batch_id,
        correlation_id=correlation_id,
        employee_count=1,
        gross=Decimal("120000000"),
        deductions=Decimal("22800000"),
        net=Decimal(net),
        payload_hash="a" * 64,
    )


def test_transfer_contract_accepts_balanced_payload() -> None:
    item = transfer()
    item.validate()
    assert_same_batch(item, transfer())


def test_transfer_contract_rejects_unbalanced_net() -> None:
    with pytest.raises(IntegrationContractError, match="gross - deductions"):
        transfer(net="97200001").validate()


def test_transfer_contract_rejects_batch_mismatch() -> None:
    with pytest.raises(IntegrationContractError, match="batch_id mismatch"):
        assert_same_batch(transfer(), transfer(batch_id="BATCH-2"))
