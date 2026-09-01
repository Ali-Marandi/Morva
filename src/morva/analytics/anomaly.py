from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Anomaly:
    code: str
    severity: str
    employee_no: str | None
    message: str
    score: Decimal


def detect_variance(employee_no: str, previous_net: Decimal, current_net: Decimal, threshold: Decimal = Decimal("0.30")) -> Anomaly | None:
    if previous_net <= 0:
        return None
    ratio = abs(current_net - previous_net) / previous_net
    if ratio <= threshold:
        return None
    direction = "increase" if current_net > previous_net else "decrease"
    return Anomaly("NET_VARIANCE", "warning", employee_no, f"unusual net {direction}: {ratio:.2%}", ratio)


def detect_duplicate_accounts(records: list[tuple[str, str]]) -> tuple[Anomaly, ...]:
    by_account: dict[str, list[str]] = {}
    for employee_no, account in records:
        by_account.setdefault(account, []).append(employee_no)
    return tuple(
        Anomaly("DUPLICATE_BANK_ACCOUNT", "critical", None, f"account {account} used by {len(ids)} employees", Decimal(len(ids)))
        for account, ids in by_account.items() if len(ids) > 1
    )
