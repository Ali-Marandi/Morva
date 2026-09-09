from decimal import Decimal

from morva.api.v1.self_service import build_payslip_pdf
from morva.persistence.domain_extensions import EmployeeCaseRecord
from morva.persistence.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_payslip_pdf_is_a_valid_pdf_header_and_contains_artifact_identity() -> None:
    pdf = build_payslip_pdf(
        employee_no="E-100",
        period="1405-05",
        currency="IRR",
        gross=Decimal("1200.0000"),
        deductions=Decimal("200.0000"),
        net=Decimal("1000.0000"),
        lines=[],
    )
    assert pdf.startswith(b"%PDF-1.4")
    assert b"Employee: E-100" in pdf
    assert b"Period: 1405-05" in pdf
    assert b"Net: 1000.0000" in pdf


def test_employee_case_persists_self_service_fields_and_resolution() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        case = EmployeeCaseRecord(
            employee_no="E-101",
            case_type="payroll",
            title="Payroll review",
            description="Please review the persisted payroll artifact.",
            priority="high",
            status="open",
            submitted_by="E-101",
        )
        session.add(case)
        session.commit()
        case.status = "resolved"
        case.response = "Evidence reviewed; no change authorized without approved source data."
        session.commit()
        loaded = session.get(EmployeeCaseRecord, case.id)
        assert loaded is not None
        assert loaded.status == "resolved"
        assert loaded.response.startswith("Evidence reviewed")
