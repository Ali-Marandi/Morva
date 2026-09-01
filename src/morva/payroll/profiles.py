from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class CalculationMode(StrEnum):
    SOURCE_REPLAY = "source_replay"
    LEGAL_CALCULATION = "legal_calculation"


class RuleReadiness(StrEnum):
    OBSERVED = "observed"
    REVIEW_REQUIRED = "review_required"
    VERIFIED = "verified"


@dataclass(frozen=True, slots=True)
class ComponentRule:
    code: str
    label: str
    mode: CalculationMode
    readiness: RuleReadiness
    taxable: bool | None
    pensionable: bool | None
    insurable: bool | None
    legal_source: str | None = None
    legal_article: str | None = None
    formula: str | None = None


@dataclass(frozen=True, slots=True)
class PayrollCalculationProfile:
    version: str
    mode: CalculationMode
    components: Mapping[str, ComponentRule]

    def require_legal_ready(self) -> None:
        if self.mode is not CalculationMode.LEGAL_CALCULATION:
            return
        blocked = [code for code, rule in self.components.items() if rule.readiness is not RuleReadiness.VERIFIED]
        if blocked:
            raise ValueError(
                "Legal calculation profile is blocked until all components are verified: "
                + ", ".join(sorted(blocked))
            )

    def component(self, code: str) -> ComponentRule:
        return self.components[code]


def observed_source_profile(component_codes: list[str]) -> PayrollCalculationProfile:
    """Build a privacy-safe profile from observed source component codes.

    Observed source data is not treated as legal truth. All legal treatments
    remain explicitly unknown until a reviewed Rule Pack provides them.
    """
    components = {
        code: ComponentRule(
            code=code,
            label=code,
            mode=CalculationMode.SOURCE_REPLAY,
            readiness=RuleReadiness.OBSERVED,
            taxable=None,
            pensionable=None,
            insurable=None,
            formula="source_value",
        )
        for code in component_codes
    }
    return PayrollCalculationProfile(
        version="SOURCE_REPLAY:1405-05:v1",
        mode=CalculationMode.SOURCE_REPLAY,
        components=components,
    )
