from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceRegistry,
)
from morva.rules.rule_pack_1405 import REQUIRED_1405_COMPONENTS


class PopulationTreatmentEvidenceError(ValueError):
    """Raised when population-scoped treatment evidence is unsafe to activate."""


ALLOWED_TREATMENTS = ("earning", "deduction")


def _timestamp(name: str, value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise PopulationTreatmentEvidenceError(
            f"{name} must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None:
        raise PopulationTreatmentEvidenceError(
            f"{name} must include a timezone"
        )
    return parsed




@dataclass(frozen=True, slots=True)
class PopulationTreatmentEvidence:
    evidence_version: int
    component_code: str
    population_scope: str
    authoritative_evidence_id: str
    treatment: str
    taxable: bool
    pensionable: bool
    insurable: bool
    reviewer_id: str
    approver_id: str
    reviewed_at: str
    approved_at: str
    status: str = "approved"

    def __post_init__(self) -> None:
        if self.evidence_version != 1:
            raise PopulationTreatmentEvidenceError(
                "unsupported population treatment evidence version"
            )
        if self.component_code not in REQUIRED_1405_COMPONENTS:
            raise PopulationTreatmentEvidenceError(
                "unsupported 1405 component"
            )
        for name, value in (
            ("population_scope", self.population_scope),
            ("authoritative_evidence_id", self.authoritative_evidence_id),
            ("reviewer_id", self.reviewer_id),
            ("approver_id", self.approver_id),
        ):
            if not value.strip():
                raise PopulationTreatmentEvidenceError(f"{name} is required")
        if self.treatment not in ALLOWED_TREATMENTS:
            raise PopulationTreatmentEvidenceError(
                "treatment must be earning or deduction"
            )
        if self.status != "approved":
            raise PopulationTreatmentEvidenceError(
                "population treatment evidence must be explicitly approved"
            )
        if self.reviewer_id.strip() == self.approver_id.strip():
            raise PopulationTreatmentEvidenceError(
                "reviewer and approver must be distinct"
            )
        reviewed_at = _timestamp("reviewed_at", self.reviewed_at)
        approved_at = _timestamp("approved_at", self.approved_at)
        if approved_at < reviewed_at:
            raise PopulationTreatmentEvidenceError(
                "approved_at cannot precede reviewed_at"
            )

    @property
    def fingerprint(self) -> str:
        payload = self.to_payload(include_fingerprint=False)
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(
        self,
        *,
        include_fingerprint: bool = True,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "evidence_version": self.evidence_version,
            "component_code": self.component_code,
            "population_scope": self.population_scope,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "treatment": self.treatment,
            "taxable": self.taxable,
            "pensionable": self.pensionable,
            "insurable": self.insurable,
            "reviewer_id": self.reviewer_id,
            "approver_id": self.approver_id,
            "reviewed_at": self.reviewed_at,
            "approved_at": self.approved_at,
            "status": self.status,
        }
        if include_fingerprint:
            payload["fingerprint"] = self.fingerprint
        return payload


@dataclass(frozen=True, slots=True)
class PopulationTreatmentSet:
    set_version: int
    population_scope: str
    items: tuple[PopulationTreatmentEvidence, ...]
    registered_at: datetime

    def __post_init__(self) -> None:
        if self.set_version != 1:
            raise PopulationTreatmentEvidenceError(
                "unsupported population treatment set version"
            )
        if not self.population_scope.strip():
            raise PopulationTreatmentEvidenceError(
                "population_scope is required"
            )
        if self.registered_at.tzinfo is None:
            raise PopulationTreatmentEvidenceError(
                "registered_at must be timezone-aware"
            )
        if not self.items:
            raise PopulationTreatmentEvidenceError(
                "population treatment set cannot be empty"
            )
        if any(
            item.population_scope.strip() != self.population_scope.strip()
            for item in self.items
        ):
            raise PopulationTreatmentEvidenceError(
                "all treatments must use the same population scope"
            )
        components = [item.component_code for item in self.items]
        if len(components) != len(set(components)):
            raise PopulationTreatmentEvidenceError(
                "duplicate component treatment evidence"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "set_version": self.set_version,
            "population_scope": self.population_scope,
            "items": [item.to_payload() for item in self.items],
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def activation_blockers(
        self,
        registry: AuthoritativeEvidenceRegistry,
        *,
        checked_at: datetime,
        require_all_1405_components: bool = True,
    ) -> tuple[str, ...]:
        if checked_at.tzinfo is None:
            raise PopulationTreatmentEvidenceError(
                "checked_at must be timezone-aware"
            )
        now = checked_at.astimezone(timezone.utc)
        by_id = {item.evidence_id: item for item in registry.items}
        blockers: list[str] = []

        if require_all_1405_components:
            missing = sorted(
                set(REQUIRED_1405_COMPONENTS)
                - {item.component_code for item in self.items}
            )
            blockers.extend(
                f"missing population treatment for component {code}"
                for code in missing
            )

        for item in self.items:
            authoritative = by_id.get(item.authoritative_evidence_id)
            if authoritative is None:
                blockers.append(
                    f"missing authoritative evidence {item.authoritative_evidence_id}"
                )
                continue
            if authoritative.source_type != "legal_rule":
                blockers.append(
                    f"component {item.component_code} is not bound to legal-rule evidence"
                )
            if authoritative.status != "accepted":
                blockers.append(
                    f"component {item.component_code} authoritative evidence is not accepted"
                )
            if (
                authoritative.population_scope.strip()
                != item.population_scope.strip()
            ):
                blockers.append(
                    f"component {item.component_code} population scope mismatch"
                )
            effective_from = _timestamp(
                "effective_from",
                authoritative.effective_from,
            )
            if effective_from > now:
                blockers.append(
                    f"component {item.component_code} legal evidence is not yet effective"
                )
            if authoritative.effective_to is not None:
                effective_to = _timestamp(
                    "effective_to",
                    authoritative.effective_to,
                )
                if effective_to <= now:
                    blockers.append(
                        f"component {item.component_code} legal evidence is no longer effective"
                    )
            approved_at = _timestamp("approved_at", authoritative.approved_at) if authoritative.approved_at else None
            if approved_at is None or approved_at > now:
                blockers.append(
                    f"component {item.component_code} legal evidence approval is not effective"
                )
            if authoritative.expires_at is not None:
                expires_at = _timestamp("expires_at", authoritative.expires_at)
                if expires_at <= now:
                    blockers.append(
                        f"component {item.component_code} legal evidence is expired"
                    )

            treatment_reviewed = _timestamp("reviewed_at", item.reviewed_at)
            treatment_approved = _timestamp("approved_at", item.approved_at)
            if treatment_reviewed > now or treatment_approved > now:
                blockers.append(
                    f"component {item.component_code} treatment approval is future-dated"
                )

        return tuple(dict.fromkeys(blockers))

    def is_activation_ready(
        self,
        registry: AuthoritativeEvidenceRegistry,
        *,
        checked_at: datetime,
        require_all_1405_components: bool = True,
    ) -> bool:
        return not self.activation_blockers(
            registry,
            checked_at=checked_at,
            require_all_1405_components=require_all_1405_components,
        )

    def to_payload(self) -> dict[str, object]:
        return {
            "set_version": self.set_version,
            "population_scope": self.population_scope,
            "items": [item.to_payload() for item in self.items],
            "registered_at": self.registered_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def build_treatment_set(
    items: tuple[PopulationTreatmentEvidence, ...],
    *,
    registered_at: datetime,
) -> PopulationTreatmentSet:
    if not items:
        raise PopulationTreatmentEvidenceError(
            "population treatment set cannot be empty"
        )
    return PopulationTreatmentSet(
        set_version=1,
        population_scope=items[0].population_scope,
        items=tuple(sorted(items, key=lambda item: item.component_code)),
        registered_at=registered_at,
    )
