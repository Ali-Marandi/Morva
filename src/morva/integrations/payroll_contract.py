from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re


_HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


class IntegrationContractError(ValueError):
    """Raised when an external payroll/finance integration payload is invalid."""


@dataclass(frozen=True, slots=True)
class PayrollTransfer:
    system: str
    batch_id: str
    correlation_id: str
    employee_count: int
    gross: Decimal
    deductions: Decimal
    net: Decimal
    payload_hash: str

    def validate(self) -> None:
        if not self.system.strip():
            raise IntegrationContractError("system is required")
        if not self.batch_id.strip() or not self.correlation_id.strip():
            raise IntegrationContractError("batch_id and correlation_id are required")
        if self.employee_count < 0:
            raise IntegrationContractError("employee_count cannot be negative")
        if min(self.gross, self.deductions, self.net) < 0:
            raise IntegrationContractError("transfer amounts cannot be negative")
        if self.gross - self.deductions != self.net:
            raise IntegrationContractError("gross - deductions must equal net")
        if not _HEX64.fullmatch(self.payload_hash):
            raise IntegrationContractError("payload_hash must be a SHA-256 hex digest")

    @classmethod
    def from_mapping(cls, payload: dict[str, object]) -> "PayrollTransfer":
        transfer = cls(
            system=str(payload.get("system", "")),
            batch_id=str(payload.get("batch_id", "")),
            correlation_id=str(payload.get("correlation_id", "")),
            employee_count=int(payload.get("employee_count", -1)),
            gross=Decimal(str(payload.get("gross", "0"))),
            deductions=Decimal(str(payload.get("deductions", "0"))),
            net=Decimal(str(payload.get("net", "0"))),
            payload_hash=str(payload.get("payload_hash", "")),
        )
        transfer.validate()
        return transfer


def assert_same_batch(*transfers: PayrollTransfer) -> None:
    if not transfers:
        return
    batch_ids = {item.batch_id for item in transfers}
    if len(batch_ids) != 1:
        raise IntegrationContractError(f"batch_id mismatch across integration systems: {sorted(batch_ids)}")
    correlations = {item.correlation_id for item in transfers}
    if len(correlations) != 1:
        raise IntegrationContractError("correlation_id mismatch across integration systems")
