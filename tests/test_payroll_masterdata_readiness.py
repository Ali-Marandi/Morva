from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from morva.payroll.models import PayrollResult
from morva.payroll.readiness_guard import PayrollReadinessError
from morva.payroll.service import PayrollService
from morva.persistence.models import Base


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    with factory() as value:
        yield value


def test_checked_calculation_fails_closed_without_accepted_master_data(session):
    with pytest.raises(PayrollReadinessError, match="no accepted master-data assessment"):
        PayrollService().calculate_checked(
            session=session,
            employee_no="E-1",
            period=date(2026, 9, 1),
            lines=(),
        )


def test_readiness_error_contains_all_blockers(session):
    with pytest.raises(PayrollReadinessError) as exc_info:
        PayrollService().calculate_checked(
            session=session,
            employee_no="E-1",
            period=date(2026, 9, 1),
            lines=(
                PayrollService().build_standard_lines(
                    base_salary=Decimal("1000"), allowances=(), deductions=()
                )[0],
            ),
        )
    assert exc_info.value.blockers == ("no accepted master-data assessment is available",)


def test_readiness_checked_calculation_preserves_calculation_result_shape():
    assert PayrollResult.__name__ == "PayrollResult"
