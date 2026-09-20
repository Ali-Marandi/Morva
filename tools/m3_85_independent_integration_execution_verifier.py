from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.independent_integration_execution_verifier import (
    IndependentIntegrationExecutionVerificationError,
    verify_integration_execution,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify M3.84 integration execution evidence"
    )
    parser.add_argument("--execution-evidence", type=Path, required=True)
    parser.add_argument("--readiness-gate", type=Path, required=True)
    parser.add_argument("--readiness-verification", type=Path, required=True)
    parser.add_argument("--registry-file", type=Path, required=True)
    parser.add_argument("--activation-gate", type=Path, required=True)
    parser.add_argument("--contract-manifest", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_integration_execution(
            execution_evidence=args.execution_evidence,
            readiness_gate=args.readiness_gate,
            readiness_verification_receipt=args.readiness_verification,
            registry_file=args.registry_file,
            activation_gate=args.activation_gate,
            contract_manifest=args.contract_manifest,
            repository=args.repository,
            candidate_sha=args.candidate_sha,
        )
        write_receipt(receipt, args.output)
    except (
        IndependentIntegrationExecutionVerificationError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(
            2,
            f"M3.85 integration execution verification blocked: {exc}\n",
        )

    print("M3.85 integration execution evidence independently verified")
    print(f"repository={receipt.repository}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"environment={receipt.target_environment}")
    print(f"execution_evidence_fingerprint={receipt.execution_evidence_fingerprint}")
    print(f"verification_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
