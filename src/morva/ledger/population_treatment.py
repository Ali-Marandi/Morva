from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from hashlib import sha256

from morva.ledger.treatments import LedgerComponent


class PopulationTreatmentStatus(StrEnum):
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"


@dataclass(frozen=True, slots=True)
class PopulationScopedLedgerTreatment:
    component: LedgerComponent
    population_id: str
    population_scope: str
    population_fingerprint: str
    rule_pack_version: str
    rule_pack_evidence_fingerprint: str
    source_id: str
    source_document_hash: str
    effective_from: date
    effective_to: date | None
    retrieved_at: datetime
    reviewer_id: str
    approver_id: str
    regression_reference: str
    taxable: bool
    pensionable: bool
    insurable: bool
    status: PopulationTreatmentStatus = PopulationTreatmentStatus.REVIEW_REQUIRED

    def validate(self) -> None:
        text_fields = (
            ("population_id", self.population_id),
            ("population_scope", self.population_scope),
            ("population_fingerprint", self.population_fingerprint),
            ("rule_pack_version", self.rule_pack_version),
            ("rule_pack_evidence_fingerprint", self.rule_pack_evidence_fingerprint),
            ("source_id", self.source_id),
            ("source_document_hash", self.source_document_hash),
            ("reviewer_id", self.reviewer_id),
            ("approver_id", self.approver_id),
            ("regression_reference", self.regression_reference),
        )
        for name, value in text_fields:
            if not value.strip():
                raise ValueError(f"{name} is required")

        for name, value in (
            ("population_fingerprint", self.population_fingerprint),
            ("rule_pack_evidence_fingerprint", self.rule_pack_evidence_fingerprint),
            ("source_document_hash", self.source_document_hash),
        ):
            if len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
                raise ValueError(f"{name} must be a 64-character SHA-256 hex digest")

        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not precede effective_from")
        if self.retrieved_at.tzinfo is None:
            raise ValueError("retrieved_at must be timezone-aware")
        if self.reviewer_id.strip() == self.approver_id.strip():
            raise ValueError("reviewer and approver must be distinct")

    def execution_ready(self, *, expected_population_fingerprint: str, expected_rule_pack_evidence_fingerprint: str) -> bool:
        try:
            self.validate()
        except ValueError:
            return False
        if self.status is not PopulationTreatmentStatus.APPROVED:
            return False
        return (
            self.population_fingerprint.lower() == expected_population_fingerprint.lower()
            and self.rule_pack_evidence_fingerprint.lower() == expected_rule_pack_evidence_fingerprint.lower()
        )

    def activation_fingerprint(self) -> str:
        self.validate()
        canonical = "|".join(
            (
                self.component.value,
                self.population_id.strip(),
                self.population_scope.strip(),
                self.population_fingerprint.lower(),
                self.rule_pack_version.strip(),
                self.rule_pack_evidence_fingerprint.lower(),
                self.source_id.strip(),
                self.source_document_hash.lower(),
                self.effective_from.isoformat(),
                self.effective_to.isoformat() if self.effective_to else "",
                self.retrieved_at.isoformat(),
                self.reviewer_id.strip(),
                self.approver_id.strip(),
                self.regression_reference.strip(),
                str(self.taxable),
                str(self.pensionable),
                str(self.insurable),
                self.status.value,
            )
        )
        return sha256(canonical.encode("utf-8")).hexdigest()
