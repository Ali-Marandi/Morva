from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import json
from typing import Mapping


class RetroGapError(ValueError):
    """Raised when retroactive-gap evidence is incomplete or inconsistent."""


@dataclass(frozen=True, slots=True)
class RetroactiveOrder:
    """حکم پرسنلی با تاریخ صدور و تاریخ اجرای مستقل و صریح."""

    employee_no: str
    order_no: str
    effective_date: date
    issue_date: date

    def __post_init__(self) -> None:
        if not self.employee_no.strip():
            raise RetroGapError("employee number is required")
        if not self.order_no.strip():
            raise RetroGapError("order number is required")
        if self.issue_date < self.effective_date:
            raise RetroGapError("issue_date cannot precede effective_date")


@dataclass(frozen=True, slots=True)
class RetroactiveGap:
    """شکاف ناشی از اجرای حکم پیش از تاریخ صدور آن."""

    employee_no: str
    order_no: str
    effective_date: date
    issue_date: date
    gap_days: int

    @property
    def detected(self) -> bool:
        return self.gap_days > 0


@dataclass(frozen=True, slots=True)
class RetroAuditTrail:
    """شاهد immutable برای بازتولید تصمیم و نتیجه محاسبه عطف‌به‌ماسبق."""

    actor_id: str
    reason: str
    calculated_at: datetime
    periods: tuple[str, ...]
    original_total: Decimal
    revised_total: Decimal
    net_arrears: Decimal
    payable_arrears: Decimal
    fingerprint: str


@dataclass(frozen=True, slots=True)
class RetroArrearsResult:
    gap: RetroactiveGap
    periods: tuple[str, ...]
    original_total: Decimal
    revised_total: Decimal
    net_arrears: Decimal
    payable_arrears: Decimal
    audit: RetroAuditTrail


def detect_retroactive_gap(order: RetroactiveOrder) -> RetroactiveGap:
    """شکاف تاریخ اجرای زودتر از تاریخ صدور را بدون استنتاج مقررات تشخیص می‌دهد."""
    gap_days = (order.issue_date - order.effective_date).days
    return RetroactiveGap(
        employee_no=order.employee_no,
        order_no=order.order_no,
        effective_date=order.effective_date,
        issue_date=order.issue_date,
        gap_days=gap_days,
    )


def _affected_periods(
    gap: RetroactiveGap,
    period_windows: Mapping[str, tuple[date, date]],
) -> tuple[str, ...]:
    if not gap.detected:
        return ()
    selected: list[str] = []
    for period, (period_start, period_end) in period_windows.items():
        if period_end < period_start:
            raise RetroGapError(f"invalid period window for {period}")
        # بازه حق عطف‌به‌ماسبق به‌صورت [effective_date, issue_date) مدل می‌شود.
        if period_start < gap.issue_date and period_end >= gap.effective_date:
            selected.append(period)
    return tuple(sorted(selected))


def calculate_gap_arrears(
    gap: RetroactiveGap,
    *,
    period_windows: Mapping[str, tuple[date, date]],
    original_nets: Mapping[str, Decimal],
    revised_nets: Mapping[str, Decimal],
    actor_id: str,
    reason: str,
    calculated_at: datetime,
) -> RetroArrearsResult:
    """مابه‌التفاوت خروجی‌های persisted را برای دوره‌های همپوشان با شکاف محاسبه می‌کند.

    این تابع هیچ نرخ یا قاعده حقوقی تولید نمی‌کند؛ فقط خروجی‌های قدیمی و اصلاح‌شده
    را با provenance زمانی مشخص مقایسه می‌کند.
    """
    if not actor_id.strip():
        raise RetroGapError("actor_id is required")
    if not reason.strip():
        raise RetroGapError("reason is required")
    periods = _affected_periods(gap, period_windows)
    if gap.detected and not periods:
        raise RetroGapError("retroactive gap has no covered payroll period")

    missing_original = sorted(set(periods) - set(original_nets))
    missing_revised = sorted(set(periods) - set(revised_nets))
    if missing_original:
        raise RetroGapError(f"missing original payroll outputs for periods: {missing_original}")
    if missing_revised:
        raise RetroGapError(f"missing revised payroll outputs for periods: {missing_revised}")

    original_total = sum((Decimal(original_nets[p]) for p in periods), Decimal("0"))
    revised_total = sum((Decimal(revised_nets[p]) for p in periods), Decimal("0"))
    net_arrears = revised_total - original_total
    payable_arrears = sum(
        (max(Decimal(revised_nets[p]) - Decimal(original_nets[p]), Decimal("0")) for p in periods),
        Decimal("0"),
    )
    canonical = {
        "employee_no": gap.employee_no,
        "order_no": gap.order_no,
        "effective_date": gap.effective_date.isoformat(),
        "issue_date": gap.issue_date.isoformat(),
        "periods": periods,
        "original_total": format(original_total, "f"),
        "revised_total": format(revised_total, "f"),
        "net_arrears": format(net_arrears, "f"),
        "payable_arrears": format(payable_arrears, "f"),
        "actor_id": actor_id,
        "reason": reason,
        "calculated_at": calculated_at.isoformat(),
    }
    fingerprint = sha256(
        json.dumps(canonical, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    audit = RetroAuditTrail(
        actor_id=actor_id,
        reason=reason,
        calculated_at=calculated_at,
        periods=periods,
        original_total=original_total,
        revised_total=revised_total,
        net_arrears=net_arrears,
        payable_arrears=payable_arrears,
        fingerprint=fingerprint,
    )
    return RetroArrearsResult(
        gap=gap,
        periods=periods,
        original_total=original_total,
        revised_total=revised_total,
        net_arrears=net_arrears,
        payable_arrears=payable_arrears,
        audit=audit,
    )
