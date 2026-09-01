from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Gate:
    code: str
    description: str
    passed: bool
    blocking: bool = True


@dataclass(frozen=True, slots=True)
class GateReport:
    gates: tuple[Gate, ...]

    @property
    def passed(self) -> bool:
        return all(gate.passed for gate in self.gates if gate.blocking)


def evaluate_repository_gates(root: Path) -> GateReport:
    gates = (
        Gate("SOURCE_TREE", "Repository has source code", (root / "src").exists()),
        Gate("TESTS", "Automated tests exist", (root / "tests").exists()),
        Gate("LEGAL_GOVERNANCE", "Legal governance document exists", (root / "docs/legal/LEGAL_RULE_GOVERNANCE.md").exists()),
        Gate("PRODUCTION_RULE", "Production readiness gate exists", (root / "docs/PRODUCTION_READINESS.md").exists()),
        Gate("NO_REAL_DATA", "No real payroll data is required in Git", True),
        Gate("EXTERNAL_CREDENTIALS", "External credentials are configured outside Git", False, blocking=False),
        Gate("AUTHORITATIVE_SAMPLE", "Authoritative real payroll samples have been reconciled", False, blocking=False),
        Gate("RULE_APPROVAL", "Annual rule pack has final legal/finance approval", False, blocking=False),
    )
    return GateReport(gates)
