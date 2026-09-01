from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ExplanationNode:
    code: str
    title: str
    amount: Decimal
    source: str | None = None
    children: tuple["ExplanationNode", ...] = ()


@dataclass(frozen=True, slots=True)
class PayrollDelta:
    code: str
    title: str
    previous: Decimal
    current: Decimal

    @property
    def change(self) -> Decimal:
        return self.current - self.previous


def compare_lines(previous: dict[str, Decimal], current: dict[str, Decimal]) -> tuple[PayrollDelta, ...]:
    keys = sorted(set(previous) | set(current))
    return tuple(
        PayrollDelta(code, code, previous.get(code, Decimal("0")), current.get(code, Decimal("0")))
        for code in keys
        if previous.get(code, Decimal("0")) != current.get(code, Decimal("0"))
    )
