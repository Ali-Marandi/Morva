from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Mapping

from morva.runtime.config import settings
from .expression import evaluate_expression


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    code: str
    title: str
    effective_from: date
    effective_to: date | None = None
    taxable: bool = False
    pensionable: bool = False
    insurable: bool = False
    formula: Callable[[Mapping[str, Decimal]], Decimal] | None = None
    expression: Mapping[str, object] | None = None
    legal_reference: str | None = None

    def is_active(self, on: date) -> bool:
        return self.effective_from <= on and (self.effective_to is None or on <= self.effective_to)


@dataclass(frozen=True, slots=True)
class RuleContext:
    effective_date: date
    values: Mapping[str, Decimal]


@dataclass(frozen=True, slots=True)
class RuleResult:
    code: str
    amount: Decimal
    explanation: str
    legal_reference: str | None = None


class RuleNotFoundError(LookupError):
    pass


class RuleEngine:
    """Deterministic, effective-dated engine with a persisted-safe expression DSL."""

    def __init__(self, definitions: list[RuleDefinition] | None = None) -> None:
        self._definitions: dict[str, list[RuleDefinition]] = {}
        for definition in definitions or []:
            self.register(definition)

    def register(self, definition: RuleDefinition) -> None:
        if definition.effective_to and definition.effective_to < definition.effective_from:
            raise ValueError("rule effective_to cannot precede effective_from")
        if settings.production and definition.formula is not None:
            raise ValueError("callable rule formulas are forbidden in production; use the safe expression DSL")
        self._definitions.setdefault(definition.code, []).append(definition)
        self._definitions[definition.code].sort(key=lambda item: item.effective_from, reverse=True)

    def resolve(self, code: str, on: date) -> RuleDefinition:
        for definition in self._definitions.get(code, []):
            if definition.is_active(on):
                return definition
        raise RuleNotFoundError(f"No active rule found for {code} on {on.isoformat()}")

    def calculate(self, code: str, context: RuleContext) -> RuleResult:
        definition = self.resolve(code, context.effective_date)
        if definition.formula is not None and definition.expression is not None:
            raise ValueError(f"Rule {code} cannot define both formula and expression")
        if definition.formula is not None:
            amount = definition.formula(context.values)
        elif definition.expression is not None:
            amount = evaluate_expression(definition.expression, context.values)
        else:
            raise ValueError(f"Rule {code} has no executable formula")
        if amount < 0:
            raise ValueError(f"Rule {code} produced a negative amount")
        explanation = f"{definition.title} [{definition.code}] applied for {context.effective_date.isoformat()}"
        return RuleResult(code, amount, explanation, definition.legal_reference)
