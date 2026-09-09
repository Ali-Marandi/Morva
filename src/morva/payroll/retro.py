from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping
from uuid import UUID

from sqlalchemy.orm import Session

from morva.persistence.enterprise_models import PayrollArtifactRecord
from morva.persistence.models import PersonnelSnapshotRecord


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
