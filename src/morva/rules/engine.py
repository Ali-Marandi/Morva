from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Mapping


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


class RuleNotFoundError(LookupError):
    pass


class RuleEngine:
    """Deterministic, effective-dated calculation engine.

    Production legal rules should be persisted/versioned in the database. Python callables
    are intentionally accepted here only as a safe execution abstraction for the first core.
    """

    def __init__(self, definitions: list[RuleDefinition] | None = None) -> None:
        self._definitions: dict[str, list[RuleDefinition]] = {}
        for definition in definitions or []:
            self.register(definition)

    def register(self, definition: RuleDefinition) -> None:
        self._definitions.setdefault(definition.code, []).append(definition)
        self._definitions[definition.code].sort(key=lambda item: item.effective_from, reverse=True)

    def resolve(self, code: str, on: date) -> RuleDefinition:
        for definition in self._definitions.get(code, []):
            if definition.is_active(on):
                return definition
        raise RuleNotFoundError(f"No active rule found for {code} on {on.isoformat()}")

    def calculate(self, code: str, context: RuleContext) -> RuleResult:
        definition = self.resolve(code, context.effective_date)
        if definition.formula is None:
            raise ValueError(f"Rule {code} has no executable formula")
        amount = definition.formula(context.values)
        if amount < 0:
            raise ValueError(f"Rule {code} produced a negative amount")
        explanation = (
            f"{definition.title} [{definition.code}] applied for "
            f"{context.effective_date.isoformat()}"
        )
        return RuleResult(code=code, amount=amount, explanation=explanation)
