from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from morva.runtime.integration_execution_readiness_gate import (
    IntegrationExecutionReadinessGateError,
    build_integration_execution_readiness_gate,
    write_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-evidence", type=Path, required=True)
    parser.add_argument("--readiness-gate", type=Path, required=True)
    parser.add_argument("--readiness-verification", type=Path, required=True)
    parser.add_argument("--registry-file", type=Path, required=True)
    parser.add_argument("--activation-gate", type=Path, required=True)
    parser.add_argument("--contract-manifest", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--checked-at")
    parser.add_argument("--max-execution-age-hours", type=int, default=24)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        checked_at = (
            datetime.fromisoformat(args.checked_at)
            if args.checked_at
            else datetime.now(timezone.utc)
        )
        gate = build_integration_execution_readiness_gate(
            execution_evidence=args.execution_evidence,
            readiness_gate=args.readiness_gate,
            readiness_verification_receipt=args.readiness_verification,
            registry_file=args.registry_file,
            activation_gate=args.activation_gate,
            contract_manifest=args.contract_manifest,
            repository=args.repository,
            candidate_sha=args.candidate_sha,
            checked_at=checked_at,
            max_execution_age_hours=args.max_execution_age_hours,
        )
        write_gate(gate, args.output)
    except (IntegrationExecutionReadinessGateError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.86 execution readiness blocked: {exc}\n")
    print("M3.86 integration execution readiness gate verified")
    print(f"fingerprint={gate.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
