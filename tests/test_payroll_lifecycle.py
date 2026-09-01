from decimal import Decimal

import pytest

from morva.payroll.lifecycle import PayrollStatus, transition
from morva.payroll.models import PayrollLine, PayrollResult
from morva.payroll.validation import PayrollValidator, has_blocking_errors


def test_payroll_status_transition():
    assert transition(PayrollStatus.DRAFT, PayrollStatus.CALCULATING) == PayrollStatus.CALCULATING
    assert transition(PayrollStatus.EXPORTED, PayrollStatus.PAID) == PayrollStatus.PAID


def test_invalid_transition_is_blocked():
    with pytest.raises(ValueError):
        transition(PayrollStatus.DRAFT, PayrollStatus.PAID)


def test_validation_detects_duplicate_components():
    result = PayrollResult(
        employee_no="E-1",
        period="1405-06",
        ruleset_version="test",
        lines=(
            PayrollLine("A", "A", Decimal("100"), "earning"),
            PayrollLine("A", "A", Decimal("100"), "earning"),
        ),
    )
    findings = PayrollValidator().validate(result)
    assert any(item.code == "DUPLICATE_COMPONENT" for item in findings)
    assert has_blocking_errors(findings) is False
