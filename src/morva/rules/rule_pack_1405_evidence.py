from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from urllib.parse import urlparse

REQUIRED_1405_COMPONENTS: tuple[str, ...] = (
    "JOB_RIGHT", "INCUMBENT_RIGHT", "JOB_ALLOWANCE", "RANK_ALLOWANCE", "FAMILY_ALLOWANCE",
    "CHILD_ALLOWANCE", "OVERTIME", "TEACHING_FEE", "REGION_WEATHER", "TAX", "PENSION",
    "INSURANCE", "LOAN", "COURT_ORDER",
)

@dataclass(frozen=True, slots=True)
class RuleComponentEvidence:
    component_code: str
    source_id: str
    citation: str
    issuer: str
    source_uri: str
    document_hash: str
    adoption_date: date
    effective_from: date
    effective_to: date | None
    retrieved_at: datetime
    reviewer_id: str
    approver_id: str
    regression_reference: str
    treatment: str
    taxable: bool | None
    pensionable: bool | None
    insurable: bool | None
    activation_status: str = "review_required"

@dataclass(frozen=True, slots=True)
class RulePackEvidenceResult:
    accepted: bool
    blockers: tuple[str, ...]
    fingerprint: str

def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdefABCDEF" for char in value)

def _fingerprint(evidence: tuple[RuleComponentEvidence, ...]) -> str:
    rows = []
    for item in sorted(evidence, key=lambda row: row.component_code):
        rows.append("|".join((
            item.component_code.strip(), item.source_id.strip(), item.document_hash.lower(),
            item.citation.strip(), item.source_uri.strip(), item.adoption_date.isoformat(),
            item.effective_from.isoformat(), item.effective_to.isoformat() if item.effective_to else "",
            item.retrieved_at.isoformat(), item.reviewer_id.strip(), item.approver_id.strip(),
            item.regression_reference.strip(), item.treatment.strip(), str(item.taxable),
            str(item.pensionable), str(item.insurable), item.activation_status.strip(),
        )))
    return sha256("\n".join(rows).encode("utf-8")).hexdigest()

def validate_1405_rule_pack_evidence(
    evidence: tuple[RuleComponentEvidence, ...],
    expected_source_ids: dict[str, str],
) -> RulePackEvidenceResult:
    blockers: list[str] = []
    by_component: dict[str, RuleComponentEvidence] = {}
    for item in evidence:
        code = item.component_code.strip()
        if not code:
            blockers.append("component_code is required")
            continue
        if code in by_component:
            blockers.append(f"duplicate evidence for component {code}")
            continue
        by_component[code] = item
        if code not in REQUIRED_1405_COMPONENTS:
            blockers.append(f"unsupported 1405 component: {code}")
        if expected_source_ids.get(code) != item.source_id.strip():
            blockers.append(f"{code} source_id does not match governed source register")
        for field_name in ("source_id", "citation", "issuer", "source_uri", "reviewer_id", "approver_id", "regression_reference"):
            if not getattr(item, field_name).strip():
                blockers.append(f"{code}.{field_name} is required")
        parsed = urlparse(item.source_uri.strip())
        if parsed.scheme != "https" or not parsed.netloc:
            blockers.append(f"{code}.source_uri must be an absolute HTTPS URI")
        if not _valid_sha256(item.document_hash):
            blockers.append(f"{code}.document_hash must be a 64-character SHA-256 hex digest")
        if item.effective_to is not None and item.effective_to < item.effective_from:
            blockers.append(f"{code}.effective_to must not precede effective_from")
        if item.retrieved_at.tzinfo is None:
            blockers.append(f"{code}.retrieved_at must be timezone-aware")
        if item.reviewer_id.strip() == item.approver_id.strip():
            blockers.append(f"{code} reviewer and approver must be distinct")
        if item.activation_status != "review_required":
            blockers.append(f"{code}.activation_status must remain review_required until formal approval")
        if item.taxable is None or item.pensionable is None or item.insurable is None:
            blockers.append(f"{code} tax/pension/insurance treatment must be explicitly resolved before activation")
        if item.treatment not in {"earning", "deduction"}:
            blockers.append(f"{code}.treatment must be earning or deduction")
    missing = sorted(set(REQUIRED_1405_COMPONENTS) - set(by_component))
    blockers.extend(f"missing evidence for component {code}" for code in missing)
    return RulePackEvidenceResult(not blockers, tuple(dict.fromkeys(blockers)), _fingerprint(tuple(by_component.values())) if by_component else "")
