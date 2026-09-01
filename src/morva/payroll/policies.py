from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from morva.runtime.config import settings


@dataclass(frozen=True, slots=True)
class TaxBracket:
    upper: Decimal | None
    rate: Decimal


@dataclass(frozen=True, slots=True)
class TaxPolicy:
    version: str
    monthly_exemption: Decimal
    brackets: tuple[TaxBracket, ...]

    def calculate(self, taxable_income: Decimal) -> tuple[Decimal, tuple[str, ...]]:
        if taxable_income <= 0:
            return Decimal(0), ("taxable income is zero or negative",)
        remaining = max(Decimal(0), taxable_income - self.monthly_exemption)
        tax = Decimal(0)
        lower = Decimal(0)
        explanations: list[str] = [f"exemption={self.monthly_exemption}"]
        for bracket in self.brackets:
            if remaining <= lower:
                break
            upper = bracket.upper if bracket.upper is not None else remaining
            width = min(remaining, upper) - lower
            if width > 0:
                tax += width * bracket.rate
                explanations.append(f"{width} at {bracket.rate}")
            lower = upper
            if bracket.upper is None or remaining <= upper:
                break
        return tax.quantize(Decimal("0.01")), tuple(explanations)


@dataclass(frozen=True, slots=True)
class ContributionPolicy:
    code: str
    rate: Decimal
    ceiling: Decimal | None = None

    def calculate(self, gross: Decimal) -> Decimal:
        base = gross if self.ceiling is None else min(gross, self.ceiling)
        return (max(Decimal(0), base) * self.rate).quantize(Decimal("0.01"))


def demo_iranian_policy_pack() -> tuple[TaxPolicy, tuple[ContributionPolicy, ...]]:
    """Development-only policy examples; never available in production."""
    if settings.production or not settings.allow_demo_policies:
        raise RuntimeError("demo policy packs are disabled; use an approved Rule Pack")
    tax = TaxPolicy(
        version="demo-1405",
        monthly_exemption=Decimal("400000000"),
        brackets=(
            TaxBracket(Decimal("700000000"), Decimal("0.10")),
            TaxBracket(Decimal("1000000000"), Decimal("0.15")),
            TaxBracket(Decimal("1400000000"), Decimal("0.20")),
            TaxBracket(None, Decimal("0.30")),
        ),
    )
    contributions = (ContributionPolicy("PENSION_DEMO", Decimal("0.09")),)
    return tax, contributions
