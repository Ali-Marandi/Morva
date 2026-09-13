from pathlib import Path
import re

from morva.rules.rule_pack_1405 import REQUIRED_1405_COMPONENTS


REGISTER_PATH = Path("docs/legal/rule-packs/1405/primary-source-register.yml")


def _text() -> str:
    return REGISTER_PATH.read_text(encoding="utf-8")


def test_register_covers_every_required_component_exactly_once():
    text = _text()
    source_ids = re.findall(r"^  - source_id: ([A-Z0-9-]+)$", text, flags=re.MULTILINE)
    assert source_ids == [
        "LMS-CSC-64-68",
        "TEACHER-RANK-REG-1404",
        "PAY-1405",
        "TAX-1405",
    ]
    component_codes = re.findall(r"^      - ([A-Z0-9_]+)$", text, flags=re.MULTILINE)
    assert sorted(component_codes) == sorted(REQUIRED_1405_COMPONENTS)
    assert len(component_codes) == len(set(component_codes))


def test_register_is_not_activation_ready():
    text = _text()
    assert "status: research_required" in text
    assert "activation_policy: \"fail_closed_until_primary_source_artifact_and_formal_approval\"" in text
    assert text.count("primary_source_locator: required") == 4
    assert text.count("evidence_status: review_required") == 4


def test_register_does_not_embed_legal_numeric_values():
    text = _text()
    forbidden_numeric_fields = ("percent:", "rate:", "threshold:", "amount:", "coefficient:")
    assert not any(marker in text.lower() for marker in forbidden_numeric_fields)
