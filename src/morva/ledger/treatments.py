from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class LedgerComponent(StrEnum):
    TAX = "TAX"
    PENSION = "PENSION"
    INSURANCE = "INSURANCE"
    LOAN = "LOAN"
    COURT_ORDER = "COURT_ORDER"


class TreatmentStatus(StrEnum):
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"


@dataclass(frozen=True, slots=True)
class LedgerTreatment:
    """Explicit legal/financial classification for a payroll ledger component.

    This object carries classification metadata only. It deliberately does not
    contain rates, thresholds, formulas or inferred legal treatment.
    """

    component: LedgerComponent
    taxable: bool
    pensionable: bool
    insurable: bool
    source: str
    reference: str
    effective_from: str
    effective_to: str | None = None
    status: TreatmentStatus = TreatmentStatus.REVIEW_REQUIRED
    reviewer: str | None = None
    approver: str | None = None
    regression_suite_hash: str | None = None

    def validate(self) -> None:
        if not self.source.strip():
            raise ValueError("source must be a non-empty string")
        if not self.reference.strip():
            raise ValueError("reference must be a non-empty string")
        if not self.effective_from.strip():
            raise ValueError("effective_from must be a non-empty string")
        if self.status is TreatmentStatus.APPROVED:
            if not self.reviewer or not self.reviewer.strip():
                raise ValueError("approved treatment requires reviewer")
            if not self.approver or not self.approver.strip():
                raise ValueError("approved treatment requires approver")
            if self.reviewer.strip() == self.approver.strip():
                raise ValueError("reviewer and approver must be distinct")
            if not self.regression_suite_hash or not self.regression_suite_hash.strip():
                raise ValueError("approved treatment requires regression_suite_hash")

    def assert_approved(self) -> None:
        self.validate()
        if self.status is not TreatmentStatus.APPROVED:
            raise RuntimeError(
                f"{self.component.value} treatment is not approved; execution remains fail-closed"
            )


@dataclass(frozen=True, slots=True)
class LedgerTreatmentCatalog:
    treatments: tuple[LedgerTreatment, ...] = ()

    def __post_init__(self) -> None:
        seen: set[LedgerComponent] = set()
        for treatment in self.treatments:
            treatment.validate()
            if treatment.component in seen:
                raise ValueError(f"duplicate treatment for {treatment.component.value}")
            seen.add(treatment.component)

    def for_component(self, component: LedgerComponent) -> LedgerTreatment:
        for treatment in self.treatments:
            if treatment.component is component:
                return treatment
        raise KeyError(component.value)

    def execution_ready(self, component: LedgerComponent) -> bool:
        try:
            self.for_component(component).assert_approved()
        except (KeyError, RuntimeError, ValueError):
            return False
        return True


REQUIRED_LEDGER_COMPONENTS = frozenset(LedgerComponent)
