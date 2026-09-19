from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.final_readiness_verifier import (
    FinalReadinessVerificationError,
    verify_final_readiness,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify the Morva final readiness gate"
    )
    parser.add_argument("--technical-gate", type=Path, required=True)
    parser.add_argument("--freshness-gate", type=Path, required=True)
    parser.add_argument("--final-gate", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_final_readiness(
            technical_gate=args.technical_gate,
            freshness_gate=args.freshness_gate,
            final_gate=args.final_gate,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
        )
        write_receipt(receipt, args.output)
    except (FinalReadinessVerificationError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.65 final readiness verification blocked: {exc}\n")

    print("M3.65 final readiness independently verified")
    print(f"repository={receipt.repository}")
    print(f"release_id={receipt.release_id}")
    print(f"tag={receipt.tag}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"final_gate_fingerprint={receipt.final_gate_fingerprint}")
    print(f"verification_fingerprint={receipt.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
