from __future__ import annotations

import argparse
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from morva.payroll.snapshot import PayrollSnapshot, latest_effective_order


def money(value: str | int | float | None) -> Decimal:
    return Decimal(str(value or "0"))


def load_bundle(path: Path) -> dict[str, list[dict]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {"payroll", "orders", "loans", "supplementary", "health", "social"}
    missing = required - payload.keys()
    if missing:
        raise ValueError(f"bundle missing sections: {sorted(missing)}")
    return payload


def build(bundle: dict[str, list[dict]]) -> list[PayrollSnapshot]:
    orders: dict[str, list[dict]] = defaultdict(list)
    loans: dict[str, list[dict]] = defaultdict(list)
    supplementary = {r["employee_key"]: r for r in bundle["supplementary"]}
    health = {r["employee_key"]: r for r in bundle["health"]}
    social = {r["employee_key"]: r for r in bundle["social"]}
    for row in bundle["orders"]:
        orders[row["employee_key"]].append(row)
    for row in bundle["loans"]:
        loans[row["employee_key"]].append(row)

    snapshots: list[PayrollSnapshot] = []
    for row in bundle["payroll"]:
        employee = row["employee_key"]
        order = latest_effective_order(orders[employee])
        installment_total = sum((money(x.get("installment")) for x in loans.get(employee, [])), Decimal("0"))
        snapshots.append(
            PayrollSnapshot(
                employee_key=employee,
                period=row["period"],
                employment_type=row.get("employment_type"),
                org_unit=row.get("org_unit"),
                service_region=row.get("service_region"),
                work_days=row.get("work_days"),
                gross=money(row.get("gross")),
                deductions=money(row.get("deductions")),
                net=money(row.get("net")),
                employer_commitments=money(row.get("employer_commitments")),
                components={k: money(v) for k, v in row.get("components", {}).items()},
                deduction_components={k: money(v) for k, v in row.get("deduction_components", {}).items()},
                latest_order=order,
                loan_installment_total=installment_total,
                loan_count=len(loans.get(employee, [])),
                supplementary=supplementary.get(employee),
                health=health.get(employee),
                social=social.get(employee),
            )
        )
    return snapshots


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Morva payroll domain snapshots from an anonymized import bundle")
    parser.add_argument("bundle")
    parser.add_argument("--output", default="morva-payroll-snapshots.json")
    args = parser.parse_args()
    snapshots = build(load_bundle(Path(args.bundle)))
    output = {
        "period": snapshots[0].period if snapshots else None,
        "population": len(snapshots),
        "snapshots": [
            {
                "employee_key": s.employee_key,
                "period": s.period,
                "employment_type": s.employment_type,
                "org_unit": s.org_unit,
                "service_region": s.service_region,
                "work_days": s.work_days,
                "gross": str(s.gross),
                "deductions": str(s.deductions),
                "net": str(s.net),
                "employer_commitments": str(s.employer_commitments),
                "components": {k: str(v) for k, v in s.components.items()},
                "deduction_components": {k: str(v) for k, v in s.deduction_components.items()},
                "latest_order": {
                    "order_number": s.latest_order.order_number,
                    "order_type": s.latest_order.order_type,
                    "effective_date": s.latest_order.effective_date,
                    "issue_date": s.latest_order.issue_date,
                    "arrears_date": s.latest_order.arrears_date,
                    "end_date": s.latest_order.end_date,
                    "status": s.latest_order.status,
                    "benefit_total": str(s.latest_order.benefit_total),
                },
                "loan_installment_total": str(s.loan_installment_total),
                "loan_count": s.loan_count,
                "supplementary_present": s.supplementary is not None,
                "health_present": s.health is not None,
                "social_present": s.social is not None,
                "unexplained_deduction_total": str(s.unexplained_deduction_total),
            }
            for s in snapshots
        ],
    }
    Path(args.output).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(snapshots)} snapshots to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
