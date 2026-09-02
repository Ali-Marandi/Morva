from __future__ import annotations

from decimal import Decimal

from morva.data_import.service_v2 import DEDUCTION_COLUMNS, GROSS_COLUMNS, money

# Deliberately conservative: only components with an explicit reviewed catalog mapping may become payable lines.
SOURCE_TO_COMPONENT = {
    "حق شغل-1": "JOB_RIGHT",
    "حق شاغل-2": "INCUMBENT_RIGHT",
    "فوق العاده شغل-22": "JOB_ALLOWANCE",
    "فوق العاده رتبه بندی-18": "RANK_ALLOWANCE",
    "فوق العاده مديريت-57": "MANAGEMENT",
    "کمک هزینه عائله مندی-11": "FAMILY",
    "کمک هزینه اولاد-12": "CHILD",
    "حق التدریس-110": "TEACHING_FEE",
    "فوق العاده بدی آب و هوا-7": "REGION_WEATHER",
    "فوق العاده سختی کار-4": "REGION_WEATHER",
    "فوق العاده ایثارگری-91": "VETERAN_ALLOWANCE",
    "مالیات-965": "TAX",
    "صندوق بازنشستگی-941": "PENSION",
    "بیمه تامین اجتماعی-943": "INSURANCE",
    "بیمه تکمیلی درمانی-934": "INSURANCE",
    "وام-999": "LOAN",
}


def project_components(source_row: dict[str, object]) -> list[dict[str, object]]:
    """Project source columns only; unresolved or zero-valued components are not payable lines."""
    projected: list[dict[str, object]] = []
    source_columns = set(GROSS_COLUMNS) | set(DEDUCTION_COLUMNS)
    for column in sorted(source_columns):
        amount = money(source_row.get(column))
        if amount == Decimal(0):
            continue
        component_code = SOURCE_TO_COMPONENT.get(column)
        if component_code is None:
            projected.append({"source_column": column, "amount": str(amount), "status": "quarantined", "reason": "no reviewed component mapping"})
            continue
        kind = "earning" if column in GROSS_COLUMNS else "deduction"
        projected.append({"source_column": column, "component_code": component_code, "amount": str(amount), "kind": kind, "status": "review_required"})
    return projected
