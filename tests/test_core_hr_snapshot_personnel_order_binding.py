from __future__ import annotations

import copy
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.persistence.models import Base, EmployeeRecord
from morva.personnel.core_hr_snapshot import build_core_hr_snapshot, persist_core_hr_snapshot
from morva.personnel.order_approval import decide_order, ensure_submission
from morva.personnel.order_approval_policy import register_approval_policy
from morva.personnel.order_registry import persist_personnel_order
from morva.personnel.orders import OrderLine, OrderType, PersonnelOrder


POLICY_CODE = "PO-SNAPSHOT-BIND"
SUBMITTER_ROLE = "personnel_operator"
APPROVER_ROLE = "personnel_approver"


def _session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _employee(session, employee_no: str = "EMP-SNAPSHOT") -> EmployeeRecord:
    employee = EmployeeRecord(
        employee_no=employee_no,
        source_employee_key=f"SRC-{employee_no}",
        national_id="1234567890",
        first_name="Snapshot",
        last_name="Binding",
        employment_type="permanent",
        status="active",
        organization_unit_id="ORG-1",
        position_id="POS-1",
    )
    session.add(employee)
    session.flush()
    return employee


def _policy(session):
    register_approval_policy(
        session,
        policy_code=POLICY_CODE,
        version="2026.1",
        order_types=["promotion"],
        required_submission_role=SUBMITTER_ROLE,
        required_decision_role=APPROVER_ROLE,
        source_reference="ORG-POLICY-SNAPSHOT-01",
        source_hash="a" * 64,
        approved_by="authority-1",
        approved_at=datetime.now(timezone.utc),
    )


def _approved_order(session, employee_no: str, number: str = "PO-SNAPSHOT-001"):
    order = PersonnelOrder(
        number=number,
        employee_no=employee_no,
        order_type=OrderType.PROMOTION,
        issue_date=date(2026, 1, 1),
        effective_from=date(2026, 2, 1),
        reference="LEGAL-REF-SNAPSHOT-001",
        lines=(OrderLine(code="BASE", amount=Decimal("100.00"), rule_code="RULE-1"),),
    )
    record = persist_personnel_order(session, order)
    ensure_submission(
        session,
        record,
        "submitter-1",
        policy_code=POLICY_CODE,
        submitted_role=SUBMITTER_ROLE,
    )
    decide_order(
        session,
        record,
        decided_by="approver-1",
        decided_role=APPROVER_ROLE,
        decision="approved",
    )
    session.flush()
    return record


def test_core_hr_snapshot_includes_effective_approved_personnel_orders():
    with _session() as session:
        employee = _employee(session)
        _policy(session)
        order = _approved_order(session, employee.employee_no)
        payload = build_core_hr_snapshot(session, employee.employee_no, date(2026, 3, 1))

        assert payload["personnel_orders"]["status"] == "reconciled"
        assert payload["personnel_orders"]["order_numbers"] == [order.order_no]
        assert payload["personnel_orders"]["order_fingerprints"] == [order.content_hash]

        snapshot = persist_core_hr_snapshot(
            session, employee.employee_no, "1405-06", date(2026, 3, 1)
        )
        assert snapshot.order_numbers == [order.order_no]
        assert snapshot.components["core_hr"]["personnel_orders"]["order_numbers"] == [order.order_no]


def test_core_hr_snapshot_fails_closed_on_approved_order_tampering():
    with _session() as session:
        employee = _employee(session, "EMP-SNAPSHOT-T")
        _policy(session)
        order = _approved_order(session, employee.employee_no, "PO-SNAPSHOT-T-001")
        payload = copy.deepcopy(order.payload)
        payload["lines"][0]["amount"] = "999.00"
        order.payload = payload
        session.commit()

        with pytest.raises(ValueError, match="effective-state reconciliation is blocked"):
            build_core_hr_snapshot(session, employee.employee_no, date(2026, 3, 1))


def test_core_hr_snapshot_is_immutable_after_order_state_is_bound():
    with _session() as session:
        employee = _employee(session, "EMP-SNAPSHOT-I")
        _policy(session)
        order = _approved_order(session, employee.employee_no, "PO-SNAPSHOT-I-001")
        snapshot = persist_core_hr_snapshot(session, employee.employee_no, "1405-06", date(2026, 3, 1))
        session.commit()

        payload = copy.deepcopy(order.payload)
        payload["lines"][0]["amount"] = "200.00"
        order.payload = payload
        session.commit()

        with pytest.raises(ValueError, match="effective-state reconciliation is blocked"):
            persist_core_hr_snapshot(session, employee.employee_no, "1405-06", date(2026, 3, 1))

        assert snapshot.order_numbers == [order.order_no]
