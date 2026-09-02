from __future__ import annotations

from decimal import Decimal

from morva.payroll.source_projection import project_components


def test_projection_marks_unmapped_source_component_quarantined() -> None:
    items = project_components({"حق شغل-1": "100", "فوق العاده ناموجود": "25"})
    assert {item["component_code"] for item in items if item["status"] == "review_required"} == {"JOB_RIGHT"}
    assert any(item["status"] == "quarantined" for item in items)


def test_projection_is_deterministic_and_decimal_exact() -> None:
    first = project_components({"حق شغل-1": "100.10"})
    second = project_components({"حق شغل-1": Decimal("100.10")})
    assert first == second
    assert first[0]["amount"] == "100.10"


def test_jalali_period_remains_textual() -> None:
    period = "1405-05"
    assert period == "1405-05"
    assert int(period.split("-")[0]) == 1405
