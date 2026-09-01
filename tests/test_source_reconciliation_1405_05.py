from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path


REPORT = Path(__file__).parents[1] / "docs" / "data-import" / "1405-05-full-reconciliation.json"


def test_1405_05_reconciliation_golden_controls() -> None:
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    assert data["source_rows"]["payroll"] == 3329
    assert data["coverage"]["payroll_to_orders"] == 3329
    assert data["reconciliation"]["gross_component_mismatches"] == 0
    assert data["reconciliation"]["net_mismatches"] == 0
    assert Decimal(data["aggregate_controls"]["gross"]) - Decimal(data["aggregate_controls"]["deductions"]) == Decimal(data["aggregate_controls"]["net"])
    assert Decimal(data["reconciliation"]["deduction_residual_total"]) == Decimal("55625337")


def test_historical_order_population_is_not_lost() -> None:
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    assert data["coverage"]["orders_only_not_in_payroll"] == 231
