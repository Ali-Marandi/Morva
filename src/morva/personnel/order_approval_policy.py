from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from morva.persistence.approval_records import PersonnelOrderApprovalPolicyRecord

_APPROVED = "approved"


def canonical_approval_policy_payload(
    *,
    policy_code: str,
    version: str,
    order_types: Iterable[str],
    required_submission_role: str,
    required_decision_role: str,
    source_reference: str,
    source_hash: str,
) -> dict[str, object]:
    normalized_types = sorted({str(item).strip() for item in order_types if str(item).strip()})
    return {
        "policy_code": policy_code.strip(),
        "version": version.strip(),
        "order_types": normalized_types,
        "required_submission_role": required_submission_role.strip(),
        "required_decision_role": required_decision_role.strip(),
        "source_reference": source_reference.strip(),
        "source_hash": source_hash.strip().lower(),
    }


def approval_policy_fingerprint(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def register_approval_policy(
    session: Session,
    *,
    policy_code: str,
    version: str,
    order_types: Iterable[str],
    required_submission_role: str,
    required_decision_role: str,
    source_reference: str,
    source_hash: str,
    approved_by: str | None = None,
    approved_at: datetime | None = None,
) -> PersonnelOrderApprovalPolicyRecord:
    payload = canonical_approval_policy_payload(
        policy_code=policy_code,
        version=version,
        order_types=order_types,
        required_submission_role=required_submission_role,
        required_decision_role=required_decision_role,
        source_reference=source_reference,
        source_hash=source_hash,
    )
    if not all(payload.values()) or not payload["order_types"]:
        raise ValueError("complete personnel order approval policy metadata is required")
    if approved_by is not None and not approved_by.strip():
        raise ValueError("approved_by is required when policy is approved")
    if approved_by is None and approved_at is not None:
        raise ValueError("approved_at requires approved_by")
    status = _APPROVED if approved_by else "review_required"
    policy_hash = approval_policy_fingerprint(payload)
    existing = session.scalar(
        select(PersonnelOrderApprovalPolicyRecord).where(
            PersonnelOrderApprovalPolicyRecord.policy_code == payload["policy_code"],
            PersonnelOrderApprovalPolicyRecord.version == payload["version"],
        )
    )
    if existing is not None:
        if existing.policy_hash != policy_hash:
            raise ValueError("approval policy already exists with different content")
        return existing
    record = PersonnelOrderApprovalPolicyRecord(
        policy_code=payload["policy_code"],
        version=payload["version"],
        order_types=payload["order_types"],
        required_submission_role=payload["required_submission_role"],
        required_decision_role=payload["required_decision_role"],
        source_reference=payload["source_reference"],
        source_hash=payload["source_hash"],
        status=status,
        approved_by=approved_by.strip() if approved_by else None,
        approved_at=approved_at,
        policy_hash=policy_hash,
    )
    session.add(record)
    session.flush()
    return record


def require_approved_policy(
    session: Session,
    *,
    policy_code: str,
    order_type: str,
    submitted_role: str,
    decided_role: str | None = None,
) -> PersonnelOrderApprovalPolicyRecord:
    policy = session.scalar(
        select(PersonnelOrderApprovalPolicyRecord)
        .where(
            PersonnelOrderApprovalPolicyRecord.policy_code == policy_code,
            PersonnelOrderApprovalPolicyRecord.status == _APPROVED,
        )
        .order_by(PersonnelOrderApprovalPolicyRecord.version.desc())
    )
    if policy is None:
        raise ValueError("approved personnel order approval policy is required")
    payload = canonical_approval_policy_payload(
        policy_code=policy.policy_code,
        version=policy.version,
        order_types=policy.order_types,
        required_submission_role=policy.required_submission_role,
        required_decision_role=policy.required_decision_role,
        source_reference=policy.source_reference,
        source_hash=policy.source_hash,
    )
    if policy.policy_hash != approval_policy_fingerprint(payload):
        raise ValueError("personnel order approval policy fingerprint mismatch")
    if order_type not in policy.order_types:
        raise ValueError("personnel order type is not covered by approval policy")
    if submitted_role.strip() != policy.required_submission_role:
        raise ValueError("personnel order submission role is not authorized by approval policy")
    if decided_role is not None and decided_role.strip() != policy.required_decision_role:
        raise ValueError("personnel order decision role is not authorized by approval policy")
    if not policy.approved_by or policy.approved_at is None:
        raise ValueError("personnel order approval policy lacks approval evidence")
    return policy
