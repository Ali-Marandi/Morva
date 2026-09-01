from __future__ import annotations

import argparse
import json
from pathlib import Path

from morva.data_import import MorvaImportService


def main() -> int:
    parser = argparse.ArgumentParser(description="Import six Morva payroll source reports")
    parser.add_argument("directory", help="Directory containing the six source XLSX reports")
    parser.add_argument("--period", default="1405-05")
    parser.add_argument("--output", default="morva-import-result.json")
    args = parser.parse_args()

    report, bundle = MorvaImportService().import_directory(args.directory, args.period)
    payload = {
        "period": report.source_period,
        "source_rows": report.source_rows,
        "unique_employees": report.unique_employees,
        "join_counts": report.join_counts,
        "aggregate_controls": {key: str(value) for key, value in report.aggregate_controls.items()},
        "exception_count": len(report.exceptions),
        "critical_exception_count": report.critical_exception_count,
        "exceptions": [
            {
                "employee_key": item.employee_key,
                "code": item.code,
                "expected": str(item.expected),
                "actual": str(item.actual),
                "delta": str(item.delta),
                "severity": item.severity,
                "details": item.details,
            }
            for item in report.exceptions
        ],
        "records": {name: [record.payload for record in records] for name, records in bundle.items()},
    }
    Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
