from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from morva.runtime.independent_adapter_evidence_verifier import (
    IndependentAdapterEvidenceVerificationError,
    verify_official_adapter_evidence,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify Morva official adapter evidence"
    )
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--checked-at", default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        checked_at = (
            datetime.fromisoformat(args.checked_at)
            if args.checked_at
            else datetime.now(timezone.utc)
        )
        receipt = verify_official_adapter_evidence(
            registry_file=args.registry,
            repository=args.repository,
            candidate_sha=args.candidate_sha,
            checked_at=checked_at,
        )
        write_receipt(receipt, args.output)
    except (
        IndependentAdapterEvidenceVerificationError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(2, f"M3.76 adapter evidence verification blocked: {exc}\n")

    print("M3.76 official adapter evidence independently verified")
    print(f"repository={receipt.repository}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"adapter_count={len(receipt.adapters)}")
    print(f"registry_fingerprint={receipt.registry_fingerprint}")
    print(f"verification_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
