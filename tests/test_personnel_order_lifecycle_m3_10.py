from __future__ import annotations

import copy
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from morva.persistence.models import AuditEventRecord, Base, EmployeeRecord
from morva.personnel.order_approval import decide_order, ensure_submission
from morva.personnel.order_approval_policy import register_approval_policy
from morva.personnel.order_registry import effective_personnel_orders, persist_personnel_order
from morva.personnel.orders import OrderLine, OrderType, PersonnelOrder


POLICY_CODE = "PO-APPROVAL-ORG"
SUBMITTER_ROLE = "personnel_operator"
APPROVER_ROLE = "personnel_approver"


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _policy(session):
    return register_approval_policy(
        session,
        policy_code=POLICY_CODE,
        version="2026.1",
        order_types=["promotion", "position_change"],
        required_submission_role=SUBMITTER_ROLE,
        required_decision_role=APPROVER_ROLE,
        source_reference="ORG-POLICY-2026-01",
        source_hash="a" * 64,
        approved_by="authority-1",
        approved_at=datetime(2026, 1, 2),
    )


def _employee(session, employee_no: str = "EMP-M3-10") -> EmployeeRecord:
    employee = EmployeeRecord(
        employee_no=employee_no,
        source_employee_key=f"SRC-{employee_no}",
        national_id="1234567890",
        first_name="Lifecycle",
        last_name="Test",
        employment_type="permanent",
        status="active",
        organization_unit_id="ORG-1",
        position_id="POS-1",
    )
    session.add(employee)
    session.flush()
    return employee


def _order(employee_no: str, number: str = "PO-M3-10-001") -> PersonnelOrder:
    return PersonnelOrder(
        number=number,
        employee_no=employee_no,
        order_type=OrderType.PROMOTION,
        issue_date=date(2026, 1, 1),
        effective_from=date(2026, 2, 1),
        reference="LEGAL-REF-001",
        lines=(OrderLine(code="BASE", amount=Decimal("100.00"), rule_code="RULE-1"),),
    )


def _event_types(session, order_id) -> set[str]:
    return set(
        session.scalars(
            select(AuditEventRecord.event_type).where(AuditEventRecord.entity_id == str(order_id))
        ).all()
    )


def test_lifecycle_requires_submission_policy_and_distinct_decider():
    with _session() as session:
        employee = _employee(session)
        _policy(session)
        record = persist_personnel_order(session, _order(employee.employee_no))
        session.commit()
        assert record.content_hash and len(record.content_hash) == 64

        with pytest.raises(ValueError, match="no submission provenance"):
            decide_order(
                session,
                record,
                decided_by="approver-1",
                decided_role=APPROVER_ROLE,
                decision="approved",
            )

        submission = ensure_submission(
            session,
            record,
            "submitter-1",
            policy_code=POLICY_CODE,
            submitted_role=SUBMITTER_ROLE,
        )
        session.commit()
        assert submission.submitted_by == "submitter-1"
        assert submission.order_fingerprint == record.content_hash
        assert submission.approval_policy_code == POLICY_CODE
        assert submission.approval_policy_hash

        with pytest.raises(ValueError, match="distinct"):
            decide_order(
                session,
                record,
                decided_by="submitter-1",
                decided_role=APPROVER_ROLE,
                decision="approved",
            )

        decision = decide_order(
            session,
            record,
            decided_by="approver-1",
            decided_role=APPROVER_ROLE,
            decision="approved",
        )
        session.commit()
        assert decision.decision == "approved"
        assert decision.order_fingerprint == record.content_hash
        assert decision.approval_policy_code == POLICY_CODE
        assert decision.approval_policy_hash == submission.approval_policy_hash
        assert {"personnel.order.submitted", "personnel.order.approved"}.issubset(_event_types(session, record.id))


def test_lifecycle_rejects_missing_or_wrong_policy_role():
    with _session() as session:
        employee = _employee(session, "EMP-M3-10-P")
        record = persist_personnel_order(session, _order(employee.employee_no, "PO-M3-10-P"))
        session.commit()
        with pytest.raises(ValueError, match="approved personnel order approval policy"):
            ensure_submission(
                session,
                record,
                "submitter-p",
                policy_code=POLICY_CODE,
                submitted_role=SUBMITTER_ROLE,
            )

        _policy(session)
        with pytest.raises(ValueError, match="submission role"):
            ensure_submission(
                session,
                record,
                "submitter-p",
                policy_code=POLICY_CODE,
                submitted_role="viewer",
            )


def test_rejection_requires_reason_and_final_decision_is_immutable():
    with _session() as session:
        employee = _employee(session, "EMP-M3-10-R")
        _policy(session)
        record = persist_personnel_order(session, _order(employee.employee_no, "PO-M3-10-002"))
        ensure_submission(
            session,
            record,
            "submitter-2",
            policy_code=POLICY_CODE,
            submitted_role=SUBMITTER_ROLE,
        )
        session.commit()

        with pytest.raises(ValueError, match="reason"):
            decide_order(
                session,
                record,
                decided_by="approver-2",
                decided_role=APPROVER_ROLE,
                decision="rejected",
            )

        decision = decide_order(
            session,
            record,
            decided_by="approver-2",
            decided_role=APPROVER_ROLE,
            decision="rejected",
            reason="insufficient evidence",
        )
        session.commit()
        assert decision.reason == "insufficient evidence"

        with pytest.raises(ValueError, match="immutable final decision"):
            decide_order(
                session,
                record,
                decided_by="approver-3",
                decided_role=APPROVER_ROLE,
                decision="approved",
            )

        assert effective_personnel_orders(session, employee.employee_no, date(2026, 3, 1)) == []
        assert "personnel.order.rejected" in _event_types(session, record.id)


def test_approved_order_is_not_effective_after_payload_tampering():
    with _session() as session:
        employee = _employee(session, "EMP-M3-10-T")
        _policy(session)
        record = persist_personnel_order(session, _order(employee.employee_no, "PO-M3-10-003"))
        ensure_submission(
            session,
            record,
            "submitter-3",
            policy_code=POLICY_CODE,
            submitted_role=SUBMITTER_ROLE,
        )
        decide_order(
            session,
            record,
            decided_by="approver-3",
            decided_role=APPROVER_ROLE,
            decision="approved",
        )
        session.commit()

        payload = copy.deepcopy(record.payload)
        payload["lines"][0]["amount"] = "999.00"
        record.payload = payload
        session.commit()
        session.expire(record)

        assert effective_personnel_orders(session, employee.employee_no, date(2026, 3, 1)) == []


def test_approved_order_is_not_effective_when_decision_fingerprint_is_tampered():
    with _session() as session:
        employee = _employee(session, "EMP-M3-10-D")
        _policy(session)
        record = persist_personnel_order(session, _order(employee.employee_no, "PO-M3-10-004"))
        ensure_submission(
            session,
            record,
            "submitter-4",
            policy_code=POLICY_CODE,
            submitted_role=SUBMITTER_ROLE,
        )
        decision = decide_order(
            session,
            record,
            decided_by="approver-4",
            decided_role=APPROVER_ROLE,
            decision="approved",
        )
        decision.order_fingerprint = "0" * 64
        session.commit()

        assert effective_personnel_orders(session, employee.employee_no, date(2026, 3, 1)) == []
