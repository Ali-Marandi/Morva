from pathlib import Path
import re

from morva.rules.rule_pack_1405 import REQUIRED_1405_COMPONENTS


MATRIX_PATH = Path("docs/legal/rule-packs/1405/component-matrix-1405.yml")


def _matrix_text() -> str:
    return MATRIX_PATH.read_text(encoding="utf-8")


def _component_blocks(text: str) -> list[str]:
    blocks = re.split(r"(?=^  - code: )", text, flags=re.MULTILINE)
    return [block for block in blocks if block.startswith("  - code: ")]


def test_1405_matrix_covers_every_required_component_once():
    text = _matrix_text()
    codes = re.findall(r"^  - code: ([A-Z0-9_]+)$", text, flags=re.MULTILINE)
    assert codes == list(REQUIRED_1405_COMPONENTS)
    assert len(codes) == len(set(codes))


def test_1405_matrix_is_fail_closed_and_review_required():
    text = _matrix_text()
    assert 'status: review_required' in text
    assert 'activation_policy: "fail_closed_until_primary_source_and_formal_approval"' in text
    assert "review_required and researched_not_activated entries cannot drive production payroll" in text


def test_1405_matrix_has_explicit_legal_and_treatment_fields_for_each_component():
    text = _matrix_text()
    component_blocks = _component_blocks(text)
    assert len(component_blocks) == len(REQUIRED_1405_COMPONENTS)
    for block in component_blocks:
        assert re.search(r"^    title: .+$", block, flags=re.MULTILINE)
        assert re.search(r"^    treatment: (earning|deduction|informational)$", block, flags=re.MULTILINE)
        assert re.search(r"^    source_id: [A-Z0-9-]+$", block, flags=re.MULTILINE)
        assert re.search(r"^    legal_article: .+$", block, flags=re.MULTILINE)
        assert re.search(r"^    legal_source_status: review_required$", block, flags=re.MULTILINE)
        for field in ("taxable", "pensionable", "insurable"):
            assert re.search(rf"^    {field}: (true|false|review_required)$", block, flags=re.MULTILINE)


def test_1405_deduction_components_are_explicitly_classified():
    text = _matrix_text()
    component_blocks = _component_blocks(text)
    expected_deductions = {"TAX", "PENSION", "INSURANCE", "LOAN", "COURT_ORDER"}
    for block in component_blocks:
        code = re.search(r"^  - code: ([A-Z0-9_]+)$", block, flags=re.MULTILINE).group(1)
        treatment = re.search(r"^    treatment: (earning|deduction|informational)$", block, flags=re.MULTILINE).group(1)
        assert (treatment == "deduction") == (code in expected_deductions)
