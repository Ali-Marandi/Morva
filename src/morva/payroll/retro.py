from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True, slots=True)
class RetroPeriod:
    period: str
    old_net: Decimal
    new_net: Decimal

    @property
    def difference(self) -> Decimal:
        return self.new_net - self.old_net


@dataclass(frozen=True, slots=True)
class RetroResult:
    periods: tuple[RetroPeriod, ...]

    @property
    def gross_difference(self) -> Decimal:
        return sum((item.difference for item in self.periods if item.difference > 0), Decimal(0))

    @property
    def net_difference(self) -> Decimal:
        return sum((item.difference for item in self.periods), Decimal(0))


def calculate_retroactive(old: Mapping[str, Decimal], new: Mapping[str, Decimal]) -> RetroResult:
    periods = tuple(
        RetroPeriod(period, old.get(period, Decimal(0)), new.get(period, Decimal(0)))
        for period in sorted(set(old) | set(new))
    )
    return RetroResult(periods)
