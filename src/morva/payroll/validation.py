from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from .models import PayrollResult


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    code: str
    severity: str
    message: str


class PayrollValidator:
    def validate(self, result: PayrollResult, *, minimum_net: Decimal | None = None) -> tuple[ValidationFinding, ...]:
        findings: list[ValidationFinding] = []
        seen: set[str] = set()
        for line in result.lines:
            if line.code in seen:
                findings.append(
                    ValidationFinding(
                        "DUPLICATE_COMPONENT",
                        "warning",
                        f"duplicate component: {line.code}",
                    )
                )
            seen.add(line.code)
            if line.amount < 0:
                findings.append(ValidationFinding("NEGATIVE_AMOUNT", "error", f"negative amount: {line.code}"))
            if line.kind == "deduction" and line.amount > result.gross:
                findings.append(ValidationFinding("EXCESS_DEDUCTION", "warning", f"deduction exceeds gross: {line.code}"))
        if result.net < 0:
            findings.append(ValidationFinding("NEGATIVE_NET", "error", "net payroll is negative"))
        if minimum_net is not None and result.net < minimum_net:
            findings.append(ValidationFinding("BELOW_MINIMUM_NET", "warning", "net is below configured threshold"))
        return tuple(findings)


def has_blocking_errors(findings: Iterable[ValidationFinding]) -> bool:
    return any(item.severity == "error" for item in findings)
