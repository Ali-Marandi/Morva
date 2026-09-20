from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.independent_integration_readiness_verifier import (
    IndependentIntegrationReadinessVerificationError,
    verify_integration_readiness,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify Morva integration readiness"
    )
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--activation-gate", type=Path, required=True)
    parser.add_argument("--contract-manifest", type=Path, required=True)
    parser.add_argument("--readiness-gate", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_integration_readiness(
            registry_file=args.registry,
            activation_gate=args.activation_gate,
            contract_manifest=args.contract_manifest,
            readiness_gate=args.readiness_gate,
            repository=args.repository,
            candidate_sha=args.candidate_sha,
        )
        write_receipt(receipt, args.output)
    except (
        IndependentIntegrationReadinessVerificationError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(2, f"M3.83 integration readiness verification blocked: {exc}\n")

    print("M3.83 integration readiness independently verified")
    print(f"repository={receipt.repository}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"target_environment={receipt.target_environment}")
    print(f"adapter_count={len(receipt.adapters)}")
    print(f"readiness_gate_fingerprint={receipt.readiness_gate_fingerprint}")
    print(f"verification_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
