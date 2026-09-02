from datetime import date

import pytest

from morva.rules.authority import AuthoritativeRule, RuleActivationStatus


def _rule(status: RuleActivationStatus, cases: tuple[str, ...] = ("G-1",)) -> AuthoritativeRule:
    return AuthoritativeRule(
        code="TEST",
        title="Test rule",
        issuer="issuer",
        source_document="source",
        article="1",
        clause="a",
        adoption_date=date(2026, 1, 1),
        effective_from=date(2026, 1, 1),
        effective_to=None,
        population_scope="public-sector",
        source_hash="a" * 64,
        activation_status=status,
        regression_case_ids=cases,
        approved_by="reviewer",
        approved_at=date(2026, 1, 2),
    )


def test_unapproved_rule_cannot_calculate() -> None:
    assert not _rule(RuleActivationStatus.LEGAL_REVIEWED).can_calculate(date(2026, 2, 1))
    with pytest.raises(ValueError):
        _rule(RuleActivationStatus.LEGAL_REVIEWED).assert_calculable(date(2026, 2, 1))


def test_approved_rule_requires_regression_evidence() -> None:
    assert not _rule(RuleActivationStatus.APPROVED, ()).can_calculate(date(2026, 2, 1))


def test_published_rule_with_evidence_can_calculate() -> None:
    assert _rule(RuleActivationStatus.PUBLISHED).can_calculate(date(2026, 2, 1))
