from morva.payroll import lifecycle, workflow


def test_workflow_is_only_a_compatibility_shim() -> None:
    assert workflow.PayrollStatus is lifecycle.PayrollStatus
    assert workflow.transition is lifecycle.transition
    assert workflow.can_transition is lifecycle.can_transition


def test_canonical_lifecycle_has_no_direct_to_approval_bypass() -> None:
    assert not lifecycle.can_transition(lifecycle.PayrollStatus.DRAFT, lifecycle.PayrollStatus.APPROVED)
    assert lifecycle.can_transition(lifecycle.PayrollStatus.DRAFT, lifecycle.PayrollStatus.DATA_RECEIVED)
    assert lifecycle.can_transition(lifecycle.PayrollStatus.DATA_RECEIVED, lifecycle.PayrollStatus.CALCULATING)
    assert lifecycle.can_transition(lifecycle.PayrollStatus.PAYMENT_CONFIRMED, lifecycle.PayrollStatus.RECONCILED)
