"""End-to-end research/demo fixture coverage; never a source of legal payroll truth."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from morva.audit.chain import AuditChain, AuditEvent
from morva.payroll import PayrollCalculator, PayrollLine
from morva.payroll.lifecycle import PayrollStatus, transition
from morva.rules import RuleContext, RuleDefinition, RuleEngine
from morva.rules.regression import fingerprint_rule_result


FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "1405-05"
    / "morva_1405_05_anonymized_fixture.json"
)

STATUS_SEQUENCE = (
    PayrollStatus.DATA_RECEIVED,
    PayrollStatus.CALCULATING,
    PayrollStatus.VALIDATING,
    PayrollStatus.REVIEWED,
    PayrollStatus.APPROVED,
    PayrollStatus.FROZEN,
    PayrollStatus.EXPORTED,
    PayrollStatus.SUBMITTED,
    PayrollStatus.PAYMENT_CONFIRMED,
    PayrollStatus.RECONCILED,
)


def test_1405_05_research_fixture_drives_full_payroll_lifecycle() -> None:
    """Uses research/demo rule expressions, not authoritative production law."""
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    sample = fixture["records"][0]
    salary = sample["salary"]

    values = {
        "job_right": Decimal(salary["حق شغل-1"]),
        "job_holder": Decimal(salary["حق شاغل-2"]),
        "hardship": Decimal(salary["فوق العاده سختی کار-4"]),
        "ranking": Decimal(salary["فوق العاده رتبه بندی-18"]),
    }

    engine = RuleEngine(
        [
            RuleDefinition(
                code="DEMO_GROSS",
                title="Research/demo gross components",
                effective_from=date(2026, 1, 1),
                expression={
                    "op": "add",
                    "args": [
                        {"op": "value", "name": "job_right"},
                        {"op": "value", "name": "job_holder"},
                        {"op": "value", "name": "hardship"},
                        {"op": "value", "name": "ranking"},
                    ],
                },
                legal_reference="research-demo:1405-05",
                taxable=True,
                pensionable=True,
                insurable=True,
            )
        ]
    )
    rule_result = engine.calculate(
        "DEMO_GROSS",
        RuleContext(date(2026, 7, 1), values),
    )

    calculation = PayrollCalculator().calculate(
        employee_no=sample["employee_key"],
        period=sample["payroll_month"],
        ruleset_version="research-demo-1405-05",
        lines=(
            PayrollLine(
                "DEMO_GROSS",
                "Research/demo gross",
                rule_result.amount,
                "earning",
                taxable=True,
                pensionable=True,
                insurable=True,
                rule_code=rule_result.code,
                explanation=rule_result.explanation,
            ),
        ),
    )

    audit = AuditChain()
    previous = PayrollStatus.DRAFT
    events = []

    for sequence, target in enumerate(STATUS_SEQUENCE, start=1):
        current = transition(previous, target)
        event = audit.append(
            AuditEvent(
                event_id=f"{sample['employee_key']}-lifecycle-{sequence}",
                event_type="payroll.lifecycle.transition",
                entity_type="payroll_run",
                entity_id=sample["employee_key"],
                actor_id=f"research-demo-actor-{sequence}",
                payload={
                    "status": current.value,
                    "sequence": sequence,
                    "rule_code": rule_result.code,
                    "rule_result_fingerprint": fingerprint_rule_result(rule_result),
                    "calculation_fingerprint": calculation.fingerprint,
                    "fixture": fixture["source_month"],
                    "authority": "research-demo-only",
                },
            )
        )
        assert current.value == event.payload["status"]
        assert event.payload["rule_code"] == rule_result.code
        assert event.payload["calculation_fingerprint"] == calculation.fingerprint
        assert event.digest() == audit.last_hash
        if event.previous_hash is not None:
            assert event.previous_hash == events[-1].digest()
        events.append(event)
        previous = current

    assert previous is PayrollStatus.RECONCILED
    assert len(events) == len(STATUS_SEQUENCE)
    assert calculation.result.ruleset_version == "research-demo-1405-05"
    assert calculation.result.net == calculation.result.gross - calculation.result.deductions
