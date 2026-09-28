from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from morva.audit.persistence import append_audit_event
from morva.persistence.enterprise_models import PayrollArtifactRecord
from morva.persistence.models import PersonnelSnapshotRecord, RetroCaseRecord


@dataclass(frozen=True, slots=True)
class ArrearsGap:
    """Detected administrative gap between legal effect and order issuance."""

    employee_no: str
    order_no: str
    effective_from: date
    issue_date: date
    gap_days: int

    @property
    def is_retroactive(self) -> bool:
        return self.issue_date > self.effective_from


def detect_arrears_gap(
    *,
    employee_no: str,
    order_no: str,
    effective_from: date,
    issue_date: date,
) -> ArrearsGap:
    # در حکم اصلاحی/بازگشت‌به‌کار، تاریخ اثر قانونی و تاریخ صدور اداری مستقل‌اند.
    # مثبت بودن فاصله نشان می‌دهد بازه‌ای برای بررسی مابه‌التفاوت وجود دارد؛ مبلغ از این تابع استنتاج نمی‌شود.
    if not employee_no.strip():
        raise ValueError("employee_no is required")
    if not order_no.strip():
        raise ValueError("order_no is required")
    if issue_date < effective_from:
        raise ValueError("issue_date cannot precede effective_from")
    return ArrearsGap(
        employee_no=employee_no,
        order_no=order_no,
        effective_from=effective_from,
        issue_date=issue_date,
        gap_days=(issue_date - effective_from).days,
    )

@dataclass(frozen=True, slots=True)
class ArrearsPeriod:
    period: str
    old_net: Decimal
    revised_net: Decimal

    @property
    def difference(self) -> Decimal:
        return self.revised_net - self.old_net


@dataclass(frozen=True, slots=True)
class ArrearsResult:
    gap: ArrearsGap
    periods: tuple[ArrearsPeriod, ...]

    @property
    def total_difference(self) -> Decimal:
        return sum((item.difference for item in self.periods), Decimal(0))


def calculate_gap_arrears(
    *,
    gap: ArrearsGap,
    original: Mapping[str, Decimal],
    revised: Mapping[str, Decimal],
) -> ArrearsResult:
    """Calculate arrears only for payroll periods whose month starts fall inside the gap.

    The function consumes already-calculated historical and revised values.
    It does not infer legal rates, attendance, deductions, or fund treatment.
    """
    from morva.calendar.jalali import jalali_month_start

    periods: list[ArrearsPeriod] = []
    for period in sorted(set(original) | set(revised)):
        try:
            month_start = jalali_month_start(period)
        except ValueError as exc:
            raise RetroMismatch(f"invalid payroll period: {period!r}") from exc
        if gap.effective_from <= month_start < gap.issue_date:
            periods.append(
                ArrearsPeriod(
                    period=period,
                    old_net=Decimal(original.get(period, Decimal(0))),
                    revised_net=Decimal(revised.get(period, Decimal(0))),
                )
            )
    return ArrearsResult(gap=gap, periods=tuple(periods))


@dataclass(frozen=True, slots=True)
class RetroPeriod:
    period: str
    old_net: Decimal
    new_net: Decimal
    original_snapshot_id: UUID | None = None
    revised_snapshot_id: UUID | None = None
    original_rule_pack_version: str | None = None
    revised_rule_pack_version: str | None = None

    @property
    def difference(self) -> Decimal:
        return self.new_net - self.old_net


@dataclass(frozen=True, slots=True)
class RetroResult:
    periods: tuple[RetroPeriod, ...]

    @property
    def gross_difference(self) -> Decimal:
        return sum((item.difference for item in self.periods if item.difference > 0), Decimal(0))

    @property
    def net_difference(self) -> Decimal:
        return sum((item.difference for item in self.periods), Decimal(0))

    @property
    def snapshot_driven(self) -> bool:
        return all(item.original_snapshot_id is not None and item.revised_snapshot_id is not None for item in self.periods)


class RetroMismatch(RuntimeError):
    """Raised when retroactive inputs cannot be proven snapshot-bound."""


def _validate_period(period: str) -> None:
    if len(period) != 7 or period[4] != "-" or not period[:4].isdigit() or not period[5:].isdigit():
        raise RetroMismatch(f"invalid payroll period: {period!r}")
    month = int(period[5:])
    if month < 1 or month > 12:
        raise RetroMismatch(f"invalid payroll period: {period!r}")


def _validate_snapshot(session: Session, *, employee_no: str, period: str, artifact: PayrollArtifactRecord) -> PersonnelSnapshotRecord:
    snapshot = session.get(PersonnelSnapshotRecord, artifact.personnel_snapshot_id)
    if snapshot is None:
        raise RetroMismatch(f"personnel snapshot not found for artifact {artifact.id}")
    if snapshot.employee_no != employee_no or snapshot.effective_period != period:
        raise RetroMismatch(f"personnel snapshot identity mismatch for artifact {artifact.id}")
    if snapshot.snapshot_hash != artifact.personnel_snapshot_hash:
        raise RetroMismatch(f"personnel snapshot hash mismatch for artifact {artifact.id}")
    return snapshot


def calculate_retroactive(old: Mapping[str, Decimal], new: Mapping[str, Decimal]) -> RetroResult:
    periods = tuple(
        RetroPeriod(period, old.get(period, Decimal(0)), new.get(period, Decimal(0)))
        for period in sorted(set(old) | set(new))
    )
    return RetroResult(periods)


def calculate_snapshot_driven_retro(
    session: Session,
    *,
    employee_no: str,
    original_artifacts: Mapping[str, UUID],
    revised_artifacts: Mapping[str, UUID],
) -> RetroResult:
    """Compare persisted original/revised payroll artifacts after proving shared snapshot binding.

    The original and revised calculations for a historical period must use the same immutable
    personnel snapshot. Legal rates/formulas are never inferred or activated here; the function
    only reconciles persisted artifact outputs and their provenance.
    """
    if not employee_no.strip():
        raise RetroMismatch("employee number is required")
    periods = sorted(set(original_artifacts) | set(revised_artifacts))
    if not periods:
        raise RetroMismatch("at least one retro period is required")

    result: list[RetroPeriod] = []
    for period in periods:
        _validate_period(period)
        original_id = original_artifacts.get(period)
        revised_id = revised_artifacts.get(period)
        if original_id is None or revised_id is None:
            raise RetroMismatch(f"both original and revised artifacts are required for {period}")

        original = session.get(PayrollArtifactRecord, original_id)
        revised = session.get(PayrollArtifactRecord, revised_id)
        if original is None or revised is None:
            raise RetroMismatch(f"payroll artifact missing for {period}")
        if original.employee_no != employee_no or revised.employee_no != employee_no:
            raise RetroMismatch(f"payroll artifact employee mismatch for {period}")
        if original.period != period or revised.period != period:
            raise RetroMismatch(f"payroll artifact period mismatch for {period}")

        original_snapshot = _validate_snapshot(session, employee_no=employee_no, period=period, artifact=original)
        revised_snapshot = _validate_snapshot(session, employee_no=employee_no, period=period, artifact=revised)
        if original_snapshot.id != revised_snapshot.id or original_snapshot.snapshot_hash != revised_snapshot.snapshot_hash:
            raise RetroMismatch(f"original and revised artifacts must share one immutable personnel snapshot for {period}")

        result.append(
            RetroPeriod(
                period=period,
                old_net=Decimal(original.net),
                new_net=Decimal(revised.net),
                original_snapshot_id=original.personnel_snapshot_id,
                revised_snapshot_id=revised.personnel_snapshot_id,
                original_rule_pack_version=original.rule_pack_version,
                revised_rule_pack_version=revised.rule_pack_version,
            )
        )

    return RetroResult(tuple(result))


def persist_arrears_case(
    session: Session,
    *,
    result: ArrearsResult,
    reason: str,
    actor_id: str,
) -> RetroCaseRecord:
    if not result.periods:
        raise RetroMismatch("arrears gap contains no payroll periods")
    if not reason.strip():
        raise ValueError("reason is required")
    if not actor_id.strip():
        raise ValueError("actor_id is required")

    original_total = sum((item.old_net for item in result.periods), Decimal(0))
    revised_total = sum((item.revised_net for item in result.periods), Decimal(0))
    case = RetroCaseRecord(
        employee_no=result.gap.employee_no,
        from_period=result.periods[0].period,
        to_period=result.periods[-1].period,
        original_total=original_total,
        recalculated_total=revised_total,
        difference=result.total_difference,
        reason=reason,
    )
    session.add(case)
    session.flush()
    append_audit_event(
        event_type="payroll.arrears.calculated",
        entity_type="retro_case",
        entity_id=case.id,
        actor_id=actor_id,
        reason=reason,
        payload={
            "employee_no": result.gap.employee_no,
            "order_no": result.gap.order_no,
            "effective_from": result.gap.effective_from.isoformat(),
            "issue_date": result.gap.issue_date.isoformat(),
            "from_period": case.from_period,
            "to_period": case.to_period,
            "before": {"net_total": str(original_total)},
            "after": {"net_total": str(revised_total)},
            "difference": str(result.total_difference),
        },
        session=session,
    )
    return case
