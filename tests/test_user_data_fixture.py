from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path


FIXTURE = Path(__file__).parents[1] / "fixtures" / "1405-05" / "morva_1405_05_anonymized_fixture.json"


def D(value: str | int | float) -> Decimal:
    return Decimal(str(value))


def test_user_fixture_is_anonymized_and_consistent() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    records = payload["records"]

    assert records
    assert payload["source_month"] == "1405-05"

    for record in records:
        assert record["employee_key"].startswith("EMP-")
        assert record["national_key"].startswith("NID-")
        assert "کد ملی" not in record
        assert "نام" not in record
        assert "نام خانوادگی" not in record

        salary = record["salary"]
        gross = D(salary["جمع مزایا"])
        deductions = D(salary["جمع کسور"])
        net = D(salary["خالص پرداختی"])
        assert gross - deductions == net

        supplementary = record["supplementary"]
        assert D(supplementary["total"]) == D(supplementary["employee_share"]) + D(
            supplementary["employee_arrears"]
        )

        health = record["health"]
        assert D(health["covered_salary"]) >= 0
        assert D(health["premium"]) >= 0

        latest = record["latest_order"]
        assert latest["effective_date"]
        assert latest["issue_date"]


def test_fixture_has_no_placeholder_tokens() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    assert "REPLACE_ME" not in text
