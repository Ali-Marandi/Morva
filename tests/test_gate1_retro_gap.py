from datetime import date, datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

import pytest

from morva.payroll.retro_gap import (
    RetroGapError,
    RetroactiveOrder,
    calculate_gap_arrears,
    detect_retroactive_gap,
)


FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
    / "1405-05"
    / "morva_1405_05_anonymized_fixture.json"
)


def test_detects_retroactive_gap_from_two_independent_dates() -> None:
    order = RetroactiveOrder(
        employee_no="EMP-7750f0161477",
        order_no="18571405001352",
        effective_date=date(2026, 3, 21),
        issue_date=date(2026, 4, 6),
    )
    gap = detect_retroactive_gap(order)
    assert gap.detected is True
    assert gap.gap_days == 16


def test_fixture_contains_golden_retroactive_order_shape() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    first = payload["records"][0]
    latest_order = first["latest_order"]
    assert latest_order["effective_date"] == "1405/01/01"
    assert latest_order["issue_date"] == "1405/01/17"
    assert latest_order["arrears_date"] == "1405/01/01"
    assert tuple(map(int, latest_order["effective_date"].split("/"))) < tuple(
        map(int, latest_order["issue_date"].split("/"))
    )

    # مبلغ خالص fixture به‌عنوان ورودی golden استفاده می‌شود؛ delta صرفاً سناریوی regression است.
    original = Decimal(first["salary"]["خالص پرداختی"])
    revised = original + Decimal("1250000")

    gap = detect_retroactive_gap(
        RetroactiveOrder(
            employee_no=first["employee_key"],
            order_no=latest_order["order_number"],
            effective_date=date(2026, 3, 21),
            issue_date=date(2026, 4, 6),
        )
    )
    result = calculate_gap_arrears(
        gap,
        period_windows={"1405-01": (date(2026, 3, 21), date(2026, 4, 20))},
        original_nets={"1405-01": original},
        revised_nets={"1405-01": revised},
        actor_id="test-gate1",
        reason="golden regression correction scenario",
        calculated_at=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
    )
    assert result.periods == ("1405-01",)
    assert result.original_total == original
    assert result.revised_total == revised
    assert result.net_arrears == Decimal("1250000")
    assert result.payable_arrears == Decimal("1250000")
    assert len(result.audit.fingerprint) == 64


def test_gap_calculation_fails_closed_on_missing_revised_period() -> None:
    gap = detect_retroactive_gap(
        RetroactiveOrder(
            employee_no="E-1",
            order_no="O-1",
            effective_date=date(2026, 3, 21),
            issue_date=date(2026, 4, 6),
        )
    )
    with pytest.raises(RetroGapError, match="missing revised"):
        calculate_gap_arrears(
            gap,
            period_windows={"1405-01": (date(2026, 3, 21), date(2026, 4, 20))},
            original_nets={"1405-01": Decimal("100")},
            revised_nets={},
            actor_id="tester",
            reason="missing output",
            calculated_at=datetime(2026, 9, 27, tzinfo=timezone.utc),
        )
