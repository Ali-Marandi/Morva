from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.models import Base, EmployeeRecord
from morva.personnel.order_approval import decide_order, ensure_submission
from morva.personnel.order_registry import effective_personnel_orders, persist_personnel_order
from morva.personnel.orders import OrderLine, OrderType, PersonnelOrder


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


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


def _order(employee_no: str) -> PersonnelOrder:
    return PersonnelOrder(
        number="PO-M3-10-001",
        employee_no=employee_no,
        order_type=OrderType.PROMOTION,
        issue_date=date(2026, 1, 1),
        effective_from=date(2026, 2, 1),
        reference="LEGAL-REF-001",
        lines=(OrderLine(code="BASE", amount=Decimal("100.00"), rule_code="RULE-1"),),
    )


def test_lifecycle_requires_submission_and_distinct_decider():
    with _session() as session:
        employee = _employee(session)
        record = persist_personnel_order(session, _order(employee.employee_no))
        session.commit()

        with pytest.raises(ValueError, match="no submission provenance"):
            decide_order(session, record, decided_by="approver-1", decision="approved")

        submission = ensure_submission(session, record, "submitter-1")
        session.commit()
        assert submission.submitted_by == "submitter-1"

        with pytest.raises(ValueError, match="distinct"):
            decide_order(session, record, decided_by="submitter-1", decision="approved")

        decision = decide_order(session, record, decided_by="approver-1", decision="approved")
        session.commit()
        assert decision.decision == "approved"


def test_rejection_requires_reason_and_final_decision_is_immutable():
    with _session() as session:
        employee = _employee(session, "EMP-M3-10-R")
        record = persist_personnel_order(session, _order(employee.employee_no))
        ensure_submission(session, record, "submitter-2")
        session.commit()

        with pytest.raises(ValueError, match="reason"):
            decide_order(session, record, decided_by="approver-2", decision="rejected")

        decision = decide_order(
            session,
            record,
            decided_by="approver-2",
            decision="rejected",
            reason="insufficient evidence",
        )
        session.commit()
        assert decision.reason == "insufficient evidence"

        with pytest.raises(ValueError, match="immutable final decision"):
            decide_order(session, record, decided_by="approver-3", decision="approved")

        assert effective_personnel_orders(session, employee.employee_no, date(2026, 3, 1)) == []
