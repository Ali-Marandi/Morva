from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any

from .models import ImportRecord, ImportReport, ReconciliationException
from .xlsx_reader import read_xlsx_table

PAYROLL_FILE = "گزارش لیست حقوق.xlsx"
SUPPLEMENTARY_FILE = "اکسل گزارش بیمه تکمیلی.xlsx"
LOAN_FILE = "اکسل گزارش کسر اقساط (1).xlsx"
ORDER_FILE = "گزارش احکام حقوقی.xlsx"
HEALTH_FILE = "گزارش بیمه خدمات درمانی.xlsx"
SOCIAL_FILE = "گزارش لیست بیمه تامین اجتماعی.xlsx"

PAYROLL_GROSS_COLUMNS = (
    "حق شغل-1", "حق شاغل-2", "تفاوت  تطبيق-3", "فوق العاده سختی کار-4",
    "فوق العاده بدی آب و هوا-7", "کمک هزینه عائله مندی-11", "کمک هزینه اولاد-12",
    "حداقل  دريافتي-13", "فوق العاده رتبه بندی-18", "ترمیم حقوق-19-19", "فوق العاده شغل-22",
    "سایر-23", "فوق العاده ایثارگری ماده 51-27", "تفاوت تطبیق موضوع جزء(2-1)بندالف تبصره15 ق ب 1403-50",
    "فوق العاده مديريت-57", "فوق العاده ی مناطق کمتر توسعه یافته-58", "فوق العاده ویژه-66",
    "حق لباس (سربازمعلم )-72", "فوق العاده ایثارگری-91", "تفاوت بند(ی) تبصره (12) ق.ج-95",
    "تفاوت جزء(1) بند(الف)تبصره(12) ق. ج-96", "فوق العاده تخصصی-99", "حق التدریس-110",
    "فوق العاده مشاغل خدماتی-113", "فوق العاده خاص-129", "برگشت مامورین خارج از کشور - بعد از 1404-131",
    "بازگشت بیمه تکمیلی-160",
)

PAYROLL_DEDUCTION_COLUMNS = (
    "بیمه تکمیلی درمانی-934", "بیمه سوانح سهم کارمند-937", "صندوق بازنشستگی-941", "مقرری-942",
    "بیمه تامین اجتماعی-943", "بیمه خدمات درمانی(سرانه)-945", "بیمه خدمات درمانی (خاص)-946",
    "بیمه عمر سهم کارمند-947", "مالیات-965", "مقرری جانباز-912",
)


def money(value: Any) -> Decimal:
    if value in (None, "", "-"):
        return Decimal("0")
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid monetary value: {value!r}")


def surrogate(prefix: str, value: Any) -> str:
    digest = sha256(str(value).strip().encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


class MorvaImportService:
    """Import the six Morva source reports into a privacy-safe canonical bundle."""

    def import_directory(self, directory: str | Path, source_period: str = "1405-05") -> tuple[ImportReport, dict[str, list[ImportRecord]]]:
        root = Path(directory)
        payroll = self._read(root / PAYROLL_FILE)
        supplementary = self._read(root / SUPPLEMENTARY_FILE)
        loans = self._read(root / LOAN_FILE)
        orders = self._read(root / ORDER_FILE)
        health = self._read(root / HEALTH_FILE)
        social = self._read(root / SOCIAL_FILE)

        payroll_by_code = {str(r["کد پرسنلی"]).strip(): r for r in payroll}
        payroll_by_nid = {str(r["کد ملی"]).strip(): r for r in payroll}
        loans_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
        orders_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in loans:
            loans_by_code[str(row["کد پرسنلی"]).strip()].append(row)
        for row in orders:
            orders_by_code[str(row["کد پرسنلی"]).strip()].append(row)

        report = ImportReport(source_period=source_period)
        report.source_rows = {
            PAYROLL_FILE: len(payroll), SUPPLEMENTARY_FILE: len(supplementary), LOAN_FILE: len(loans),
            ORDER_FILE: len(orders), HEALTH_FILE: len(health), SOCIAL_FILE: len(social),
        }
        report.unique_employees = len(payroll_by_code)
        report.join_counts = {
            "payroll_supplementary": sum(1 for r in supplementary if str(r.get("کد پرسنلی", "")).strip() in payroll_by_code),
            "payroll_loans": len(set(loans_by_code) & set(payroll_by_code)),
            "payroll_orders": len(set(orders_by_code) & set(payroll_by_code)),
            "payroll_social_security": sum(1 for r in social if str(r.get("کد پرسنلی", "")).strip() in payroll_by_code),
            "payroll_health_by_national_id": sum(1 for r in health if str(r.get("شماره ملی", "")).strip() in payroll_by_nid),
        }

        for row in payroll:
            code = str(row["کد پرسنلی"]).strip()
            gross = money(row["جمع مزایا"])
            deductions = money(row["جمع کسور"])
            net = money(row["خالص پرداختی"])
            gross_from_components = sum((money(row.get(c)) for c in PAYROLL_GROSS_COLUMNS), Decimal("0"))
            payroll_deductions = sum((money(row.get(c)) for c in PAYROLL_DEDUCTION_COLUMNS), Decimal("0"))
            loan_installments = sum((money(x.get("مبلغ هر قسط")) for x in loans_by_code.get(code, [])), Decimal("0"))
            if gross_from_components != gross:
                report.exceptions.append(ReconciliationException(
                    surrogate("EMP", code), "PAYROLL_GROSS_COMPONENT_MISMATCH", gross_from_components, gross,
                    gross - gross_from_components, PAYROLL_FILE, "critical",
                ))
            if gross - deductions != net:
                report.exceptions.append(ReconciliationException(
                    surrogate("EMP", code), "PAYROLL_NET_MISMATCH", gross - deductions, net,
                    net - (gross - deductions), PAYROLL_FILE, "critical",
                ))
            residual = deductions - payroll_deductions - loan_installments
            if residual:
                report.exceptions.append(ReconciliationException(
                    surrogate("EMP", code), "PAYROLL_DEDUCTION_RESIDUAL", payroll_deductions + loan_installments,
                    deductions, residual, PAYROLL_FILE, "warning", "Unclassified deduction line remains outside listed payroll deduction columns/loan installments.",
                ))

        report.aggregate_controls = {
            "payroll_gross": sum((money(r.get("جمع مزایا")) for r in payroll), Decimal("0")),
            "payroll_deductions": sum((money(r.get("جمع کسور")) for r in payroll), Decimal("0")),
            "payroll_net": sum((money(r.get("خالص پرداختی")) for r in payroll), Decimal("0")),
            "employer_commitments": sum((money(r.get("مجموع تعهدات کارفرما")) for r in payroll), Decimal("0")),
            "loan_installments": sum((money(r.get("مبلغ هر قسط")) for r in loans), Decimal("0")),
            "supplementary_employee_share": sum((money(r.get("سهم کارمند")) for r in supplementary), Decimal("0")),
            "supplementary_total": sum((money(r.get("جمع کل")) for r in supplementary), Decimal("0")),
            "health_premium": sum((money(r.get("حق بیمه")) for r in health), Decimal("0")),
            "social_employee_premium": sum((money(r.get("بیمه")) for r in social), Decimal("0")),
            "social_employer_premium": sum((money(r.get("بیمه سهم کارفرما")) for r in social), Decimal("0")),
        }

        bundle = {
            "payroll": [self._payroll_record(r, source_period) for r in payroll],
            "supplementary": [self._supp_record(r, source_period) for r in supplementary],
            "loans": [self._loan_record(r, source_period) for r in loans],
            "orders": [self._order_record(r, source_period) for r in orders],
            "health": [self._health_record(r, source_period) for r in health],
            "social": [self._social_record(r, source_period) for r in social],
        }
        return report, bundle

    @staticmethod
    def _read(path: Path) -> list[dict[str, Any]]:
        _, _, records = read_xlsx_table(path)
        return records

    @staticmethod
    def _base(row: dict[str, Any], source: str, period: str) -> dict[str, Any]:
        code = str(row.get("کد پرسنلی", "")).strip()
        nid = str(row.get("کد ملی", row.get("شماره ملی", ""))).strip()
        return {"employee_key": surrogate("EMP", code), "national_key": surrogate("NID", nid) if nid else None, "source": source, "period": period}

    def _payroll_record(self, row: dict[str, Any], period: str) -> ImportRecord:
        payload = self._base(row, PAYROLL_FILE, period)
        payload.update({"employment_type": str(row.get("نوع استخدام", "")).strip(), "org_unit": str(row.get("واحد سازمانی", "")).strip(), "service_region": str(row.get("منطقه خدمت", "")).strip(), "treasury_code": str(row.get("TREASURY_CODE", "")).strip()})
        payload["work_days"] = row.get("کارکرد عادی")
        payload["gross"] = str(money(row.get("جمع مزایا")))
        payload["deductions"] = str(money(row.get("جمع کسور")))
        payload["employer_commitments"] = str(money(row.get("مجموع تعهدات کارفرما")))
        payload["net"] = str(money(row.get("خالص پرداختی")))
        payload["components"] = {c: str(money(row.get(c))) for c in PAYROLL_GROSS_COLUMNS if c in row}
        payload["deduction_components"] = {c: str(money(row.get(c))) for c in PAYROLL_DEDUCTION_COLUMNS if c in row}
        return ImportRecord(payload["employee_key"], PAYROLL_FILE, period, payload)

    def _supp_record(self, row: dict[str, Any], period: str) -> ImportRecord:
        payload = self._base(row, SUPPLEMENTARY_FILE, period)
        payload.update({"region_code": str(row.get("کد منطقه خدمت", "")).strip(), "employee_share": str(money(row.get("سهم کارمند"))), "employee_arrears": str(money(row.get("سهم کارمند معوقه"))), "employer_share": str(money(row.get("سهم کارفرما"))), "total": str(money(row.get("جمع کل")))})
        return ImportRecord(payload["employee_key"], SUPPLEMENTARY_FILE, period, payload)

    def _loan_record(self, row: dict[str, Any], period: str) -> ImportRecord:
        payload = self._base(row, LOAN_FILE, period)
        payload.update({"loan_title": row.get("عنوان وام"), "loan_group": row.get("گروه وام"), "loan_code": row.get("کد وام"), "installment": str(money(row.get("مبلغ هر قسط"))), "remaining_balance": str(money(row.get("باقیمانده وام"))), "principal": str(money(row.get("اصل وام"))), "installment_count": row.get("تعداد اقساط"), "deduction_date": row.get("تاریخ کسر قسط")})
        return ImportRecord(payload["employee_key"], LOAN_FILE, period, payload)

    def _order_record(self, row: dict[str, Any], period: str) -> ImportRecord:
        payload = self._base(row, ORDER_FILE, period)
        payload.update({"order_type": row.get("نوع حکم"), "effective_date": row.get("تاریخ موثر"), "issue_date": row.get("تاریخ صدور"), "arrears_date": row.get("تاریخ معوق"), "end_date": row.get("تاریخ پایان"), "order_number": row.get("شماره حکم"), "status": row.get("وضعیت پرسنل"), "benefit_total": str(money(row.get("جمع مزایای حکمی")))})
        return ImportRecord(payload["employee_key"], ORDER_FILE, period, payload)

    def _health_record(self, row: dict[str, Any], period: str) -> ImportRecord:
        payload = self._base(row, HEALTH_FILE, period)
        payload.update({"covered_salary": str(money(row.get("حقوق مشمول"))), "premium": str(money(row.get("حق بیمه"))), "arrears_covered_salary": str(money(row.get("حقوق معوقه مشمول"))), "dependents": [row.get("تعداد تبعی 1"), row.get("تعداد تبعی 2"), row.get("تعداد تبعی 3")]})
        return ImportRecord(payload["employee_key"], HEALTH_FILE, period, payload)

    def _social_record(self, row: dict[str, Any], period: str) -> ImportRecord:
        payload = self._base(row, SOCIAL_FILE, period)
        payload.update({"insurance_code": row.get("کد بیمه"), "days": row.get("روز"), "monthly_wage": str(money(row.get("دستمزد ماهانه"))), "monthly_benefits": str(money(row.get("مزایای ماهانه"))), "insured_income": str(money(row.get("درآمد مشمول بیمه"))), "noninsured_income": str(money(row.get("درآمد غیر مشمول بیمه"))), "employee_premium": str(money(row.get("بیمه"))), "employer_premium": str(money(row.get("بیمه سهم کارفرما"))), "job_title": row.get("JOB_TITLE")})
        return ImportRecord(payload["employee_key"], SOCIAL_FILE, period, payload)
