from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from morva.runtime.integration_readiness_gate import (
    IntegrationReadinessGateError,
    build_integration_readiness_gate,
    write_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build Morva integration readiness evidence"
    )
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--activation-gate", type=Path, required=True)
    parser.add_argument("--activation-verification-receipt", type=Path, required=True)
    parser.add_argument("--contract-manifest", type=Path, required=True)
    parser.add_argument("--contract-verification-receipt", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument(
        "--target-environment",
        choices=("staging", "pilot"),
        required=True,
    )
    parser.add_argument("--checked-at", default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        checked_at = (
            datetime.fromisoformat(args.checked_at)
            if args.checked_at
            else datetime.now(timezone.utc)
        )
        gate = build_integration_readiness_gate(
            registry_file=args.registry,
            activation_gate=args.activation_gate,
            activation_verification_receipt=args.activation_verification_receipt,
            contract_manifest=args.contract_manifest,
            contract_verification_receipt=args.contract_verification_receipt,
            repository=args.repository,
            candidate_sha=args.candidate_sha,
            target_environment=args.target_environment,
            checked_at=checked_at,
        )
        write_gate(gate, args.output)
    except (IntegrationReadinessGateError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.82 integration readiness blocked: {exc}\n")

    print("M3.82 integration readiness gate created")
    print(f"repository={gate.repository}")
    print(f"candidate_sha={gate.candidate_sha}")
    print(f"target_environment={gate.target_environment}")
    print(f"adapter_count={len(gate.adapters)}")
    print(f"fingerprint={gate.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
