from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from morva.integrations.ports import IntegrationPayload, IntegrationReceipt


class StatutoryFund(StrEnum):
    CENTRAL_CIVIL_SERVANTS_PENSION = "central_civil_servants_pension"
    SOCIAL_SECURITY = "social_security"


@dataclass(frozen=True, slots=True)
class StatutoryFundTreatment:
    """Provider-specific classification metadata; no rates or formulas are stored here."""

    fund: StatutoryFund
    component_code: str
    source: str
    reference: str
    effective_from: str
    effective_to: str | None = None
    status: str = "review_required"
    reviewer: str | None = None
    approver: str | None = None
    regression_suite_hash: str | None = None

    def validate(self) -> None:
        if not self.component_code.strip():
            raise ValueError("component_code is required")
        if not self.source.strip():
            raise ValueError("source is required")
        if not self.reference.strip():
            raise ValueError("reference is required")
        if not self.effective_from.strip():
            raise ValueError("effective_from is required")
        if self.status == "approved":
            if not self.reviewer or not self.reviewer.strip():
                raise ValueError("approved treatment requires reviewer")
            if not self.approver or not self.approver.strip():
                raise ValueError("approved treatment requires approver")
            if self.reviewer.strip() == self.approver.strip():
                raise ValueError("reviewer and approver must be distinct")
            if not self.regression_suite_hash or not self.regression_suite_hash.strip():
                raise ValueError("approved treatment requires regression_suite_hash")


@dataclass(frozen=True, slots=True)
class StatutoryFundTreatmentCatalog:
    fund: StatutoryFund
    treatments: tuple[StatutoryFundTreatment, ...] = ()

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for treatment in self.treatments:
            if treatment.fund is not self.fund:
                raise ValueError("treatment belongs to a different statutory fund")
            treatment.validate()
            if treatment.component_code in seen:
                raise ValueError(f"duplicate treatment for {treatment.component_code}")
            seen.add(treatment.component_code)

    def for_component(self, component_code: str) -> StatutoryFundTreatment:
        for treatment in self.treatments:
            if treatment.component_code == component_code:
                return treatment
        raise KeyError(component_code)

    def execution_ready(self, component_code: str) -> bool:
        try:
            treatment = self.for_component(component_code)
            treatment.validate()
        except (KeyError, ValueError):
            return False
        return treatment.status == "approved"


class CentralCivilServantsPensionPort(Protocol):
    """Explicit integration boundary for the Central Civil Servants Pension Fund."""

    def submit_contribution(self, payload: IntegrationPayload) -> IntegrationReceipt: ...

    def health(self) -> bool: ...


class SocialSecurityPort(Protocol):
    """Explicit integration boundary for the Social Security Organization."""

    def submit_contribution(self, payload: IntegrationPayload) -> IntegrationReceipt: ...

    def health(self) -> bool: ...


class StatutoryFundIntegrationNotConfigured(RuntimeError):
    pass


class FailClosedStatutoryFundAdapter:
    """Default adapter: provider execution is impossible until approved evidence exists."""

    def __init__(self, fund: StatutoryFund) -> None:
        self.fund = fund

    def submit_contribution(self, _payload: IntegrationPayload) -> IntegrationReceipt:
        raise StatutoryFundIntegrationNotConfigured(
            f"statutory fund integration is not configured: {self.fund.value}"
        )

    def health(self) -> bool:
        return False
