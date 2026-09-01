from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from morva.data_import.service_v2 import DEDUCTION_COLUMNS, GROSS_COLUMNS, MorvaImportService, money


FIXTURE = Path(__file__).parents[1] / "fixtures" / "1405-05" / "morva_1405_05_anonymized_fixture.json"


def test_money_preserves_exact_decimal_values() -> None:
    assert money("97,140,581.40") == Decimal("97140581.40")


def test_source_component_boundaries_are_explicit() -> None:
    assert "بازگشت بیمه تکمیلی-160" in GROSS_COLUMNS
    assert "مالیات-965" in DEDUCTION_COLUMNS
    assert len(GROSS_COLUMNS) == 27
    assert len(DEDUCTION_COLUMNS) == 10


def test_anonymized_fixture_matches_import_contract() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert payload["source_month"] == "1405-05"
    assert len(payload["records"]) >= 3
    for record in payload["records"]:
        assert record["employee_key"].startswith("EMP-")
        assert record["national_key"].startswith("NID-")
        assert "نام" not in record
        assert "کد ملی" not in record


def test_service_exposes_six_source_reader() -> None:
    service = MorvaImportService()
    assert callable(service.import_directory)
