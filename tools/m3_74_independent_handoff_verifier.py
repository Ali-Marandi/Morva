from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.independent_handoff_verifier import (
    IndependentHandoffVerificationError,
    verify_handoff,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify a Morva production-readiness handoff"
    )
    parser.add_argument("--convergence-file", type=Path, required=True)
    parser.add_argument("--handoff-file", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_handoff(
            convergence_file=args.convergence_file,
            handoff_file=args.handoff_file,
            source_root=args.source_root,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
        )
        write_receipt(receipt, args.output)
    except (
        IndependentHandoffVerificationError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(2, f"M3.74 handoff verification blocked: {exc}\n")

    print("M3.74 readiness handoff independently verified")
    print(f"repository={receipt.repository}")
    print(f"release_id={receipt.release_id}")
    print(f"tag={receipt.tag}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"convergence_fingerprint={receipt.convergence_fingerprint}")
    print(f"handoff_fingerprint={receipt.handoff_fingerprint}")
    print(f"verification_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
