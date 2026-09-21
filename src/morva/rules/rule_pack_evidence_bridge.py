from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceRegistry,
)
from morva.rules.rule_pack_1405 import REQUIRED_1405_COMPONENTS
from morva.rules.rule_pack_1405_evidence import RuleComponentEvidence


class RulePackEvidenceBridgeError(ValueError):
    """Raised when 1405 component evidence cannot bind to authoritative evidence."""


@dataclass(frozen=True, slots=True)
class RulePackEvidenceBinding:
    binding_version: int
    rule_pack_version: str
    component_code: str
    population_scope: str
    authoritative_evidence_id: str
    source_id: str
    document_hash: str
    citation: str
    regression_reference: str
    treatment: str
    taxable: bool
    pensionable: bool
    insurable: bool
    bound_by: str
    bound_at: datetime

    def __post_init__(self) -> None:
        if self.binding_version != 1:
            raise RulePackEvidenceBridgeError(
                "unsupported rule-pack evidence binding version"
            )
        if self.rule_pack_version != "1405":
            raise RulePackEvidenceBridgeError(
                "rule_pack_version must be 1405"
            )
        if self.component_code not in REQUIRED_1405_COMPONENTS:
            raise RulePackEvidenceBridgeError(
                "unsupported 1405 component"
            )
        for name, value in (
            ("population_scope", self.population_scope),
            ("authoritative_evidence_id", self.authoritative_evidence_id),
            ("source_id", self.source_id),
            ("citation", self.citation),
            ("regression_reference", self.regression_reference),
            ("bound_by", self.bound_by),
        ):
            if not value.strip():
                raise RulePackEvidenceBridgeError(f"{name} is required")
        if self.treatment not in {"earning", "deduction"}:
            raise RulePackEvidenceBridgeError(
                "treatment must be earning or deduction"
            )
        if len(self.document_hash) != 64 or any(
            char not in "0123456789abcdef"
            for char in self.document_hash.lower()
        ):
            raise RulePackEvidenceBridgeError(
                "document_hash must be SHA-256"
            )
        if self.bound_at.tzinfo is None:
            raise RulePackEvidenceBridgeError(
                "bound_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "binding_version": self.binding_version,
            "rule_pack_version": self.rule_pack_version,
            "component_code": self.component_code,
            "population_scope": self.population_scope,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "source_id": self.source_id,
            "document_hash": self.document_hash.lower(),
            "citation": self.citation,
            "regression_reference": self.regression_reference,
            "treatment": self.treatment,
            "taxable": self.taxable,
            "pensionable": self.pensionable,
            "insurable": self.insurable,
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.astimezone(timezone.utc).isoformat(),
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "binding_version": self.binding_version,
            "rule_pack_version": self.rule_pack_version,
            "component_code": self.component_code,
            "population_scope": self.population_scope,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "source_id": self.source_id,
            "document_hash": self.document_hash,
            "citation": self.citation,
            "regression_reference": self.regression_reference,
            "treatment": self.treatment,
            "taxable": self.taxable,
            "pensionable": self.pensionable,
            "insurable": self.insurable,
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.astimezone(timezone.utc).isoformat(),
            "fingerprint": self.fingerprint,
        }


def build_rule_pack_evidence_binding(
    evidence: RuleComponentEvidence,
    registry: AuthoritativeEvidenceRegistry,
    *,
    population_scope: str,
    authoritative_evidence_id: str,
    bound_by: str,
    bound_at: datetime,
) -> RulePackEvidenceBinding:
    if not population_scope.strip():
        raise RulePackEvidenceBridgeError("population_scope is required")
    if not authoritative_evidence_id.strip():
        raise RulePackEvidenceBridgeError(
            "authoritative_evidence_id is required"
        )
    if not bound_by.strip():
        raise RulePackEvidenceBridgeError("bound_by is required")
    if bound_at.tzinfo is None:
        raise RulePackEvidenceBridgeError(
            "bound_at must be timezone-aware"
        )

    authoritative = next(
        (
            item
            for item in registry.items
            if item.evidence_id == authoritative_evidence_id
        ),
        None,
    )
    if authoritative is None:
        raise RulePackEvidenceBridgeError(
            "authoritative legal evidence is not present in registry"
        )
    if authoritative.source_type != "legal_rule":
        raise RulePackEvidenceBridgeError(
            "rule-pack evidence requires legal_rule authoritative evidence"
        )
    if authoritative.status != "accepted":
        raise RulePackEvidenceBridgeError(
            "authoritative legal evidence must be accepted"
        )
    if evidence.activation_status != "review_required":
        raise RulePackEvidenceBridgeError(
            "rule evidence must remain review_required until formal activation"
        )
    if evidence.component_code not in REQUIRED_1405_COMPONENTS:
        raise RulePackEvidenceBridgeError(
            "unsupported 1405 component"
        )
    if not evidence.source_id.strip():
        raise RulePackEvidenceBridgeError("source_id is required")
    if evidence.document_hash.lower() != authoritative.source_sha256.lower():
        raise RulePackEvidenceBridgeError(
            "rule evidence document hash does not match authoritative evidence SHA-256"
        )
    if evidence.source_uri.strip() != authoritative.source_uri.strip():
        raise RulePackEvidenceBridgeError(
            "rule evidence source URI does not match authoritative evidence"
        )
    if evidence.issuer.strip() != authoritative.issuer.strip():
        raise RulePackEvidenceBridgeError(
            "rule evidence issuer does not match authoritative evidence"
        )
    if authoritative.population_scope.strip() != population_scope.strip():
        raise RulePackEvidenceBridgeError(
            "authoritative evidence population scope does not match binding"
        )
    if not evidence.citation.strip() or not evidence.regression_reference.strip():
        raise RulePackEvidenceBridgeError(
            "citation and regression reference are required"
        )
    if not evidence.reviewer_id.strip() or not evidence.approver_id.strip():
        raise RulePackEvidenceBridgeError(
            "reviewer and approver are required"
        )
    if evidence.reviewer_id.strip() == evidence.approver_id.strip():
        raise RulePackEvidenceBridgeError(
            "reviewer and approver must be distinct"
        )
    if evidence.treatment not in {"earning", "deduction"}:
        raise RulePackEvidenceBridgeError(
            "treatment must be earning or deduction"
        )
    if (
        evidence.taxable is None
        or evidence.pensionable is None
        or evidence.insurable is None
    ):
        raise RulePackEvidenceBridgeError(
            "tax/pension/insurance classification must be explicit"
        )

    bound_at_utc = bound_at.astimezone(timezone.utc)
    if authoritative.approved_at is None:
        raise RulePackEvidenceBridgeError(
            "authoritative evidence approval is required"
        )
    approved_at = datetime.fromisoformat(authoritative.approved_at)
    if approved_at > bound_at_utc:
        raise RulePackEvidenceBridgeError(
            "binding precedes authoritative evidence approval"
        )
    effective_from = datetime.fromisoformat(authoritative.effective_from)
    if effective_from > bound_at_utc:
        raise RulePackEvidenceBridgeError(
            "authoritative legal evidence is not yet effective"
        )
    if authoritative.effective_to is not None:
        effective_to = datetime.fromisoformat(authoritative.effective_to)
        if effective_to <= bound_at_utc:
            raise RulePackEvidenceBridgeError(
                "authoritative legal evidence is no longer effective"
            )
    if authoritative.expires_at is not None:
        expires_at = datetime.fromisoformat(authoritative.expires_at)
        if expires_at <= bound_at_utc:
            raise RulePackEvidenceBridgeError(
                "authoritative legal evidence is expired"
            )

    return RulePackEvidenceBinding(
        binding_version=1,
        rule_pack_version="1405",
        component_code=evidence.component_code,
        population_scope=population_scope.strip(),
        authoritative_evidence_id=authoritative.evidence_id,
        source_id=evidence.source_id.strip(),
        document_hash=evidence.document_hash.lower(),
        citation=evidence.citation.strip(),
        regression_reference=evidence.regression_reference.strip(),
        treatment=evidence.treatment,
        taxable=bool(evidence.taxable),
        pensionable=bool(evidence.pensionable),
        insurable=bool(evidence.insurable),
        bound_by=bound_by.strip(),
        bound_at=bound_at_utc,
    )
