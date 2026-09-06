from datetime import date
from decimal import Decimal

import pytest

from morva.audit.chain import AuditChain, AuditEvent
from morva.budget.scenario import PayrollScenario, summarize
from morva.personnel.digital_twin import build_snapshot
from morva.personnel.orders import OrderLine, OrderType, PersonnelOrder
from morva.payroll.reconciliation import reconcile_totals
from morva.payroll.workflow import PayrollStatus, transition
from morva.rank.models import RankAssessment, RankCase, RankCaseStatus, TeacherRank


def test_payroll_workflow_blocks_invalid_transition() -> None:
    assert transition(PayrollStatus.DRAFT, PayrollStatus.DATA_RECEIVED) == PayrollStatus.DATA_RECEIVED
    assert transition(PayrollStatus.DATA_RECEIVED, PayrollStatus.CALCULATING) == PayrollStatus.CALCULATING
    with pytest.raises(ValueError):
        transition(PayrollStatus.DRAFT, PayrollStatus.APPROVED)


def test_payroll_workflow_requires_review_before_approval() -> None:
    assert transition(PayrollStatus.VALIDATING, PayrollStatus.REVIEWED) == PayrollStatus.REVIEWED
    assert transition(PayrollStatus.REVIEWED, PayrollStatus.APPROVED) == PayrollStatus.APPROVED
    with pytest.raises(ValueError):
        transition(PayrollStatus.VALIDATING, PayrollStatus.APPROVED)


def test_audit_chain_links_events() -> None:
    chain = AuditChain()
    first = chain.append(AuditEvent("1", "order.created", "order", "O1", "u1", {"x": 1}))
    second = chain.append(AuditEvent("2", "order.approved", "order", "O1", "u2", {"x": 2}))
    assert second.previous_hash == first.digest()
    assert chain.last_hash == second.digest()


def test_reconciliation_detects_mismatch() -> None:
    findings = reconcile_totals(
        morva={"net": Decimal("100.00")},
        external={"net": Decimal("90.00")},
    )
    assert len(findings) == 1
    assert findings[0].difference == Decimal("10.00")


def test_digital_twin_uses_effective_orders() -> None:
    orders = (
        PersonnelOrder(
            number="O1",
            employee_no="E1",
            order_type=OrderType.APPOINTMENT,
            issue_date=date(2024, 1, 1),
            effective_from=date(2024, 1, 1),
            effective_to=date(2024, 12, 31),
            lines=(OrderLine("JOB_RIGHT", Decimal("100")),),
        ),
        PersonnelOrder(
            number="O2",
            employee_no="E1",
            order_type=OrderType.PROMOTION,
            issue_date=date(2025, 1, 1),
            effective_from=date(2025, 1, 1),
            lines=(OrderLine("JOB_RIGHT", Decimal("200")),),
        ),
    )
    snapshot = build_snapshot(
        employee_no="E1",
        effective_date=date(2025, 2, 1),
        position_id="P1",
        employment_type="permanent",
        organization_unit_id="U1",
        orders=orders,
    )
    assert snapshot.order_numbers == ("O2",)
    assert snapshot.components == (("JOB_RIGHT", Decimal("200")),)


def test_rank_assessment_is_weighted_and_case_requires_assessment() -> None:
    case = RankCase("E1", TeacherRank.ASSISTANT_PROFESSOR, date(2026, 1, 1))
    with pytest.raises(ValueError):
        case.approve()
    case = RankCase(
        "E1",
        TeacherRank.ASSISTANT_PROFESSOR,
        date(2026, 1, 1),
        status=RankCaseStatus.COMMITTEE_REVIEW,
        assessment=RankAssessment(
            Decimal("120"), Decimal("160"), Decimal("180"), Decimal("170")
        ),
    )
    approved = case.approve()
    assert approved.status == RankCaseStatus.APPROVED


def test_budget_scenario_projects_totals() -> None:
    scenario = PayrollScenario("1406 +20%", coefficient_change=Decimal("0.20"))
    summary = summarize(scenario, [Decimal("100"), Decimal("200")])
    assert summary.projected_total == Decimal("360.00")
    assert summary.delta == Decimal("60.00")
