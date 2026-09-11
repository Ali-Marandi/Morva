from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.models import Base, EmployeeRecord
from morva.personnel.order_approval import decide_order, ensure_submission
from morva.personnel.order_approval_policy import register_approval_policy
from morva.personnel.order_registry import (
    reconcile_personnel_order_effective_state,
    persist_personnel_order,
)
from morva.personnel.orders import OrderLine, OrderType, PersonnelOrder


POLICY_CODE = "PO-RECON-TEST"
SUBMISSION_ROLE = "personnel_operator"
DECISION_ROLE = "personnel_approver"


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _seed(session, employee_no: str = "EMP-RECON-001") -> EmployeeRecord:
    employee = EmployeeRecord(
        employee_no=employee_no,
        source_employee_key=f"SRC-{employee_no}",
        national_id="1234567890",
        first_name="Reconcile",
        last_name="Test",
        employment_type="permanent",
        status="active",
        organization_unit_id="ORG-1",
        position_id="POS-1",
    )
    session.add(employee)
    register_approval_policy(
        session,
        policy_code=POLICY_CODE,
        version="2026.1",
        order_types=["promotion"],
        required_submission_role=SUBMISSION_ROLE,
        required_decision_role=DECISION_ROLE,
        source_reference="ORG-POLICY-RECON-2026",
        source_hash="b" * 64,
        approved_by="authority-1",
        approved_at=datetime(2026, 1, 2),
    )
    session.flush()
    return employee


def _order(employee_no: str, number: str = "PO-RECON-001") -> PersonnelOrder:
    return PersonnelOrder(
        number=number,
        employee_no=employee_no,
        order_type=OrderType.PROMOTION,
        issue_date=date(2026, 1, 1),
        effective_from=date(2026, 2, 1),
        reference="LEGAL-RECON-001",
        lines=(OrderLine(code="BASE", amount=Decimal("100.00"), rule_code="RULE-1"),),
    )


def _approve(session, record, suffix: str = "1") -> None:
    ensure_submission(
        session,
        record,
        f"submitter-{suffix}",
        policy_code=POLICY_CODE,
        submitted_role=SUBMISSION_ROLE,
    )
    decide_order(
        session,
        record,
        decided_by=f"approver-{suffix}",
        decided_role=DECISION_ROLE,
        decision="approved",
    )
    session.commit()


def test_reconciliation_returns_approved_effective_order():
    with _session() as session:
        employee = _seed(session)
        record = persist_personnel_order(session, _order(employee.employee_no))
        _approve(session, record)

        result = reconcile_personnel_order_effective_state(session, employee.employee_no, date(2026, 3, 1))

        assert result.status == "reconciled"
        assert not result.blocking
        assert [item.order_no for item in result.orders] == [record.order_no]
        assert result.blockers == ()


def test_reconciliation_blocks_tampered_order_instead_of_silently_dropping_it():
    with _session() as session:
        employee = _seed(session, "EMP-RECON-002")
        record = persist_personnel_order(session, _order(employee.employee_no, "PO-RECON-002"))
        _approve(session, record, "2")

        payload = deepcopy(record.payload)
        payload["lines"][0]["amount"] = "999.00"
        record.payload = payload
        session.commit()
        session.expire(record)

        result = reconcile_personnel_order_effective_state(session, employee.employee_no, date(2026, 3, 1))

        assert result.status == "blocked"
        assert result.orders == ()
        assert any(item.startswith("order-fingerprint-mismatch:PO-RECON-002") for item in result.blockers)

        with pytest.raises(ValueError, match="effective-state reconciliation is blocked"):
            from morva.personnel.order_registry import effective_personnel_orders

            effective_personnel_orders(session, employee.employee_no, date(2026, 3, 1))


def test_reconciliation_blocks_missing_submission_provenance():
    with _session() as session:
        employee = _seed(session, "EMP-RECON-003")
        record = persist_personnel_order(session, _order(employee.employee_no, "PO-RECON-003"))
        decision = __import__("morva.persistence.approval_records", fromlist=["PersonnelOrderDecisionRecord"]).PersonnelOrderDecisionRecord(
            order_id=record.id,
            order_no=record.order_no,
            decision="approved",
            decided_by="approver-3",
            decided_role=DECISION_ROLE,
            decided_at=datetime(2026, 2, 1),
            order_fingerprint=record.content_hash,
            approval_policy_code=POLICY_CODE,
            approval_policy_hash="b" * 64,
        )
        session.add(decision)
        session.commit()

        result = reconcile_personnel_order_effective_state(session, employee.employee_no, date(2026, 3, 1))

        assert result.status == "blocked"
        assert any(item == "submission-missing:PO-RECON-003" for item in result.blockers)
