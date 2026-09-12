from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from morva.masterdata.readiness import verify_master_data_readiness


@dataclass(frozen=True, slots=True)
class PayrollReadinessError(ValueError):
    blockers: tuple[str, ...]

    def __str__(self) -> str:
        return "payroll input rejected: " + "; ".join(self.blockers)


def require_master_data_readiness(
    session: Session,
    *,
    dataset_name: str | None = None,
    dataset_sha256: str | None = None,
) -> None:
    readiness = verify_master_data_readiness(
        session,
        dataset_name=dataset_name,
        dataset_sha256=dataset_sha256,
    )
    if not readiness.ready:
        raise PayrollReadinessError(readiness.blockers)
