from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
from pathlib import Path

from morva.payroll.rule_driven import RuleDrivenComponent, RuleDrivenPayroll
from morva.rules.engine import RuleDefinition, RuleEngine
from morva.rules.pack_manifest import RulePackManifest, RulePackNotProductionReadyError


FIXTURE = Path(__file__).parents[2] / "fixtures" / "golden" / "m2" / "synthetic_approved_1405.json"


def _engine() -> RuleEngine:
    return RuleEngine(
        [
            RuleDefinition(
                "JOB_RIGHT",
                "Job right",
                date(2026, 3, 21),
                expression={"op": "value", "name": "job_right"},
            ),
            RuleDefinition(
                "JOB_ALLOWANCE",
                "Job allowance",
                date(2026, 3, 21),
                expression={"op": "value", "name": "job_allowance"},
            ),
            RuleDefinition(
                "TAX",
                "Synthetic tax",
                date(2026, 3, 21),
                expression={
                    "op": "mul",
                    "args": [
                        {"op": "value", "name": "taxable_base"},
                        {"op": "const", "value": "0.10"},
                    ],
                },
            ),
            RuleDefinition(
                "PENSION",
                "Synthetic pension",
                date(2026, 3, 21),
                expression={
                    "op": "mul",
                    "args": [
                        {"op": "value", "name": "pension_base"},
                        {"op": "const", "value": "0.09"},
                    ],
                },
            ),
        ]
    )


def test_synthetic_pack_has_complete_1405_coverage() -> None:
    manifest = RulePackManifest.load(FIXTURE)
    assert manifest.synthetic is True
    assert set(manifest.components) >= {"TAX", "PENSION", "INSURANCE", "LOAN", "COURT_ORDER"}


def test_production_gate_rejects_synthetic_pack() -> None:
    manifest = RulePackManifest.load(FIXTURE)
    try:
        manifest.assert_production_ready()
    except RulePackNotProductionReadyError:
        pass
    else:
        raise AssertionError("synthetic pack must never pass production gate")


def test_end_to_end_rule_driven_payroll() -> None:
    manifest = RulePackManifest.load(FIXTURE)
    payroll = RuleDrivenPayroll(_engine(), manifest)
    result = payroll.calculate(
        employee_no="E2E-0001",
        period="1405-01",
        effective_date=date(2026, 4, 1),
        values={
            "job_right": Decimal("100000000"),
            "job_allowance": Decimal("20000000"),
            "taxable_base": Decimal("120000000"),
            "pension_base": Decimal("120000000"),
        },
        components=(
            RuleDrivenComponent(
                "JOB_RIGHT", "Job right", "earning", taxable=True, pensionable=True, insurable=True
            ),
            RuleDrivenComponent(
                "JOB_ALLOWANCE", "Job allowance", "earning", taxable=True, pensionable=True, insurable=True
            ),
            RuleDrivenComponent("TAX", "Synthetic tax", "deduction"),
            RuleDrivenComponent("PENSION", "Synthetic pension", "deduction"),
        ),
        production=False,
    )

    assert result.gross == Decimal("120000000.00")
    assert result.deductions == Decimal("22800000.00")
    assert result.net == Decimal("97200000.00")
    assert result.ruleset_version == "1405.0-test"


def test_fixture_is_valid_json() -> None:
    with FIXTURE.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    assert payload["status"] == "approved"
    assert payload["synthetic"] is True
