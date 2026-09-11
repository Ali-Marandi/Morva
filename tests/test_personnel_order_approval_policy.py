from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from morva.persistence.models import Base
from morva.personnel.order_approval_policy import register_approval_policy, require_approved_policy


def _session() -> Session:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return Session(engine, autoflush=False, future=True)


def _approved_policy(session: Session):
    return register_approval_policy(
        session,
        policy_code="PO-APPROVAL-ORG",
        version="2026.1",
        order_types=["promotion", "position_change"],
        required_submission_role="personnel_operator",
        required_decision_role="personnel_approver",
        source_reference="ORG-POLICY-2026-01",
        source_hash="a" * 64,
        approved_by="authority-1",
        approved_at=datetime(2026, 1, 2),
    )


def test_policy_is_persisted_and_fail_closed_until_approved():
    with _session() as session:
        draft = register_approval_policy(
            session,
            policy_code="PO-DRAFT",
            version="1",
            order_types=["promotion"],
            required_submission_role="personnel_operator",
            required_decision_role="personnel_approver",
            source_reference="ORG-DRAFT",
            source_hash="b" * 64,
        )
        session.commit()
        assert draft.status == "review_required"
        with pytest.raises(ValueError, match="approved"):
            require_approved_policy(
                session,
                policy_code="PO-DRAFT",
                order_type="promotion",
                submitted_role="personnel_operator",
            )


def test_policy_requires_covered_type_and_exact_roles():
    with _session() as session:
        policy = _approved_policy(session)
        session.commit()
        assert len(policy.policy_hash) == 64

        resolved = require_approved_policy(
            session,
            policy_code=policy.policy_code,
            order_type="promotion",
            submitted_role="personnel_operator",
            decided_role="personnel_approver",
        )
        assert resolved.policy_hash == policy.policy_hash

        with pytest.raises(ValueError, match="not covered"):
            require_approved_policy(
                session,
                policy_code=policy.policy_code,
                order_type="retirement",
                submitted_role="personnel_operator",
            )
        with pytest.raises(ValueError, match="submission role"):
            require_approved_policy(
                session,
                policy_code=policy.policy_code,
                order_type="promotion",
                submitted_role="viewer",
            )
        with pytest.raises(ValueError, match="decision role"):
            require_approved_policy(
                session,
                policy_code=policy.policy_code,
                order_type="promotion",
                submitted_role="personnel_operator",
                decided_role="viewer",
            )


def test_policy_fingerprint_tampering_fails_closed():
    with _session() as session:
        policy = _approved_policy(session)
        policy.source_reference = "tampered"
        session.commit()
        with pytest.raises(ValueError, match="fingerprint"):
            require_approved_policy(
                session,
                policy_code=policy.policy_code,
                order_type="promotion",
                submitted_role="personnel_operator",
            )
