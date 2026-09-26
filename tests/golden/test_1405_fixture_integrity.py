from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path


FIXTURE = Path(__file__).parents[2] / "fixtures" / "1405-05" / "morva_1405_05_anonymized_fixture.json"


def test_1405_fixture_has_stable_period_and_record_shape() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert payload["source_month"] == "1405-05"
    assert len(payload["records"]) == 3
    for record in payload["records"]:
        assert record["payroll_month"] == "1405-05"
        order = record["latest_order"]
        assert order["effective_date"]
        assert order["issue_date"]
        assert order["order_number"]


def test_1405_fixture_net_identity_is_reproducible() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    for record in payload["records"]:
        salary = record["salary"]
        benefits = Decimal(salary["جمع مزایا"])
        deductions = Decimal(salary["جمع کسور"])
        net = Decimal(salary["خالص پرداختی"])
        assert benefits - deductions == net


def test_1405_fixture_does_not_claim_legal_rule_authority() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    assert "purpose" in payload["notes"]
    assert "source_files" in payload["notes"]
    assert "raw national IDs" in payload["notes"]["identifiers"]
