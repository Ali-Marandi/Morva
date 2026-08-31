from __future__ import annotations

from datetime import date
from decimal import Decimal

from .engine import RuleDefinition, RuleEngine


def demo_ruleset() -> RuleEngine:
    """Minimal non-legal demonstration ruleset used for development and tests.

    Real Iranian payroll rules must be loaded from reviewed, versioned legal data before
    production use. Nothing in this module claims to represent current law.
    """
    return RuleEngine([
        RuleDefinition(
            code="ALLOWANCE_PERCENT",
            title="Percentage allowance",
            effective_from=date(2026, 1, 1),
            formula=lambda values: values.get("base", Decimal(0)) * values.get("rate", Decimal(0)),
        ),
        RuleDefinition(
            code="DEDUCTION_PERCENT",
            title="Percentage deduction",
            effective_from=date(2026, 1, 1),
            formula=lambda values: values.get("base", Decimal(0)) * values.get("rate", Decimal(0)),
        ),
    ])
