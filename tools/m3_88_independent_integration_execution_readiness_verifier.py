from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.independent_integration_execution_readiness_verifier import (
    IndependentIntegrationExecutionReadinessVerificationError,
    verify_execution_readiness,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify Morva M3.86 execution readiness"
    )
    for name in (
        "execution-evidence",
        "readiness-gate",
        "readiness-verification-receipt",
        "registry-file",
        "activation-gate",
        "contract-manifest",
        "execution-readiness-gate",
    ):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        receipt = verify_execution_readiness(
            execution_evidence=args.execution_evidence,
            readiness_gate=args.readiness_gate,
            readiness_verification_receipt=args.readiness_verification_receipt,
            registry_file=args.registry_file,
            activation_gate=args.activation_gate,
            contract_manifest=args.contract_manifest,
            execution_readiness_gate=args.execution_readiness_gate,
            repository=args.repository,
            candidate_sha=args.candidate_sha,
        )
        write_receipt(receipt, args.output)
    except (
        IndependentIntegrationExecutionReadinessVerificationError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(2, f"M3.88 verification blocked: {exc}\n")
    print("M3.88 integration execution readiness independently verified")
    print(f"fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
