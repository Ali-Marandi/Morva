from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from morva.runtime.independent_integration_contract_verifier import (
    IndependentIntegrationContractVerificationError,
    verify_integration_contract,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify the Morva integration contract"
    )
    parser.add_argument("--manifest", type=Path, required=True)
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
        receipt = verify_integration_contract(
            manifest_file=args.manifest,
            repository=args.repository,
            candidate_sha=args.candidate_sha,
            checked_at=checked_at,
        )
        write_receipt(receipt, args.output)
    except (
        IndependentIntegrationContractVerificationError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(2, f"M3.81 integration contract verification blocked: {exc}\n")

    print("M3.81 integration contract independently verified")
    print(f"repository={receipt.repository}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"adapter_count={len(receipt.adapters)}")
    print(f"manifest_fingerprint={receipt.manifest_fingerprint}")
    print(f"verification_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
