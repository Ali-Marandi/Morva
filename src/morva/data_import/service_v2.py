from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Any

from .models import ImportRecord, ImportReport, ReconciliationException
from .xlsx_reader import read_xlsx_table

SOURCES = {"payroll": "گزارش لیست حقوق.xlsx", "supplementary": "اکسل گزارش بیمه تکمیلی.xlsx", "loans": "اکسل گزارش کسر اقساط (1).xlsx", "orders": "گزارش احکام حقوقی.xlsx", "health": "گزارش بیمه خدمات درمانی.xlsx", "social": "گزارش لیست بیمه تامین اجتماعی.xlsx"}
GROSS_COLUMNS = ("حق شغل-1", "حق شاغل-2", "تفاوت  تطبيق-3", "فوق العاده سختی کار-4", "فوق العاده بدی آب و هوا-7", "کمک هزینه عائله مندی-11", "کمک هزینه اولاد-12", "حداقل  دريافتي-13", "فوق العاده رتبه بندی-18", "ترمیم حقوق-19-19", "فوق العاده شغل-22", "سایر-23", "فوق العاده ایثارگری ماده 51-27", "تفاوت تطبیق موضوع جزء(2-1)بندالف تبصره15 ق ب 1403-50", "فوق العاده مديريت-57", "فوق العاده ی مناطق کمتر توسعه یافته-58", "فوق العاده ویژه-66", "حق لباس (سربازمعلم )-72", "فوق العاده ایثارگری-91", "تفاوت بند(ی) تبصره (12) ق.ج-95", "تفاوت جزء(1) بند(الف)تبصره(12) ق. ج-96", "فوق العاده تخصصی-99", "حق التدریس-110", "فوق العاده مشاغل خدماتی-113", "فوق العاده خاص-129", "برگشت مامورین خارج از کشور - بعد از 1404-131", "بازگشت بیمه تکمیلی-160")
DEDUCTION_COLUMNS = ("بیمه تکمیلی درمانی-934", "بیمه سوانح سهم کارمند-937", "صندوق بازنشستگی-941", "مقرری-942", "بیمه تامین اجتماعی-943", "بیمه خدمات درمانی(سرانه)-945", "بیمه خدمات درمانی (خاص)-946", "بیمه عمر سهم کارمند-947", "مالیات-965", "مقرری جانباز-912")


def money(value: Any) -> Decimal:
    if value in (None, "", "-"):
        return Decimal(0)
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc


def key(prefix: str, value: Any) -> str:
    return f"{prefix}-{sha256(str(value).strip().encode()).hexdigest()[:16]}"


def read(path: Path) -> list[dict[str, Any]]:
    return read_xlsx_table(path)[2]


class MorvaImportService:
    """Deterministic, privacy-safe six-report importer and reconciliation engine."""

    def import_directory(self, directory: str | Path, source_period: str = "1405-05") -> tuple[ImportReport, dict[str, list[ImportRecord]]]:
        root = Path(directory)
        tables = {name: read(root / filename) for name, filename in SOURCES.items()}
        payroll = tables["payroll"]
        payroll_by_code = {str(row["کد پرسنلی"]).strip(): row for row in payroll}
        payroll_by_nid = {str(row["کد ملی"]).strip(): row for row in payroll}
        loans_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
        orders_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in tables["loans"]:
            loans_by_code[str(row["کد پرسنلی"]).strip()].append(row)
        for row in tables["orders"]:
            orders_by_code[str(row["کد پرسنلی"]).strip()].append(row)

        report = ImportReport(source_period=source_period)
        report.source_rows = {name: len(rows) for name, rows in tables.items()}
        report.unique_employees = len(payroll_by_code)
        report.join_counts = {
            "payroll_supplementary": sum(str(row.get("کد پرسنلی", "")).strip() in payroll_by_code for row in tables["supplementary"]),
            "payroll_loans": len(set(loans_by_code) & set(payroll_by_code)),
            "payroll_orders": len(set(orders_by_code) & set(payroll_by_code)),
            "payroll_social_security": sum(str(row.get("کد پرسنلی", "")).strip() in payroll_by_code for row in tables["social"]),
            "payroll_health_by_national_id": sum(str(row.get("شماره ملی", "")).strip() in payroll_by_nid for row in tables["health"]),
        }

        for row in payroll:
            employee = key("EMP", row["کد پرسنلی"])
            gross = money(row.get("جمع مزایا"))
            deductions = money(row.get("جمع کسور"))
            net = money(row.get("خالص پرداختی"))
            gross_components = sum((money(row.get(column)) for column in GROSS_COLUMNS), Decimal(0))
            explicit_deductions = sum((money(row.get(column)) for column in DEDUCTION_COLUMNS), Decimal(0))
            installments = sum((money(item.get("مبلغ هر قسط")) for item in loans_by_code.get(str(row["کد پرسنلی"]).strip(), [])), Decimal(0))
            if gross_components != gross:
                report.exceptions.append(ReconciliationException(employee, "GROSS_COMPONENT_MISMATCH", gross_components, gross, gross - gross_components, SOURCES["payroll"], "critical"))
            if gross - deductions != net:
                report.exceptions.append(ReconciliationException(employee, "NET_MISMATCH", gross - deductions, net, net - (gross - deductions), SOURCES["payroll"], "critical"))
            residual = deductions - explicit_deductions - installments
            if residual:
                report.exceptions.append(ReconciliationException(employee, "DEDUCTION_BRIDGE_RESIDUAL", explicit_deductions + installments, deductions, residual, SOURCES["payroll"], "warning", "Requires classification against source deduction details."))

        report.aggregate_controls = {
            "payroll_gross": sum((money(row.get("جمع مزایا")) for row in payroll), Decimal(0)),
            "payroll_deductions": sum((money(row.get("جمع کسور")) for row in payroll), Decimal(0)),
            "payroll_net": sum((money(row.get("خالص پرداختی")) for row in payroll), Decimal(0)),
            "employer_commitments": sum((money(row.get("مجموع تعهدات کارفرما")) for row in payroll), Decimal(0)),
            "loan_installments": sum((money(row.get("مبلغ هر قسط")) for row in tables["loans"]), Decimal(0)),
            "supplementary_employee_share": sum((money(row.get("سهم کارمند")) for row in tables["supplementary"]), Decimal(0)),
            "supplementary_total": sum((money(row.get("جمع کل")) for row in tables["supplementary"]), Decimal(0)),
            "health_premium": sum((money(row.get("حق بیمه")) for row in tables["health"]), Decimal(0)),
            "social_employee_premium": sum((money(row.get("بیمه")) for row in tables["social"]), Decimal(0)),
            "social_employer_premium": sum((money(row.get("بیمه سهم کارفرما")) for row in tables["social"]), Decimal(0)),
        }

        bundle: dict[str, list[ImportRecord]] = {name: [] for name in tables}
        for row in payroll:
            employee = key("EMP", row["کد پرسنلی"])
            components = {column: str(money(row.get(column))) for column in (*GROSS_COLUMNS, *DEDUCTION_COLUMNS) if money(row.get(column)) != 0}
            bundle["payroll"].append(ImportRecord(employee, SOURCES["payroll"], source_period, {"employee_key": employee, "national_key": key("NID", row["کد ملی"]), "gross": str(money(row["جمع مزایا"])), "deductions": str(money(row["جمع کسور"])), "net": str(money(row["خالص پرداختی"])), "components": components}))
        for name in ("supplementary", "loans", "orders", "social"):
            for row in tables[name]:
                employee = key("EMP", row["کد پرسنلی"])
                bundle[name].append(ImportRecord(employee, SOURCES[name], source_period, {"employee_key": employee, "source_row": row}))
        for row in tables["health"]:
            nid = str(row["شماره ملی"]).strip()
            employee = key("EMP", payroll_by_nid[nid]["کد پرسنلی"]) if nid in payroll_by_nid else None
            bundle["health"].append(ImportRecord(employee or key("UNMATCHED", nid), SOURCES["health"], source_period, {"employee_key": employee, "national_key": key("NID", nid), "covered_salary": str(money(row.get("حقوق مشمول"))), "premium": str(money(row.get("حق بیمه")))}))
        return report, bundle
