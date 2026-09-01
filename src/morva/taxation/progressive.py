from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class TaxBand:
    lower: Decimal
    upper: Decimal | None
    rate: Decimal


@dataclass(frozen=True, slots=True)
class ProgressiveTaxPolicy:
    version: str
    annual_exemption: Decimal
    bands: tuple[TaxBand, ...]

    def calculate_annual(self, annual_taxable_income: Decimal) -> Decimal:
        income = max(Decimal(0), annual_taxable_income)
        taxable_after_exemption = max(Decimal(0), income - self.annual_exemption)
        tax = Decimal(0)
        for band in self.bands:
            upper = band.upper if band.upper is not None else taxable_after_exemption
            if taxable_after_exemption <= band.lower:
                continue
            slice_amount = min(taxable_after_exemption, upper) - band.lower
            if slice_amount > 0:
                tax += slice_amount * band.rate
            if band.upper is None or taxable_after_exemption <= band.upper:
                break
        return tax.quantize(Decimal("0.01"))


RESEARCH_1405 = ProgressiveTaxPolicy(
    version="1405-research-1",
    annual_exemption=Decimal("4800000000"),
    bands=(
        TaxBand(Decimal("0"), Decimal("4800000000"), Decimal("0")),
        TaxBand(Decimal("4800000000"), Decimal("9600000000"), Decimal("0.10")),
        TaxBand(Decimal("9600000000"), Decimal("12000000000"), Decimal("0.15")),
        TaxBand(Decimal("12000000000"), Decimal("14400000000"), Decimal("0.20")),
        TaxBand(Decimal("14400000000"), Decimal("16800000000"), Decimal("0.25")),
        TaxBand(Decimal("16800000000"), None, Decimal("0.30")),
    ),
)
