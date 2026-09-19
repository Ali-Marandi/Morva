from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.production_promotion_gate import ProductionPromotionGateError
from morva.runtime.production_promotion_verifier import (
    verify_production_promotion,
    write_verification_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify a Morva production-promotion gate"
    )
    parser.add_argument("--bundle-archive", type=Path, required=True)
    parser.add_argument("--bundle-metadata", type=Path, required=True)
    parser.add_argument("--promotion-gate", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--deployment-attestation", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_production_promotion(
            bundle_archive=args.bundle_archive,
            bundle_metadata=args.bundle_metadata,
            promotion_gate=args.promotion_gate,
            authorization=args.authorization,
            deployment_attestation=args.deployment_attestation,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
        )
        write_verification_receipt(receipt, args.output)
    except (ProductionPromotionGateError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.60 promotion verification blocked: {exc}\n")

    print("M3.60 production-promotion evidence independently verified")
    print(f"repository={receipt.repository}")
    print(f"release_id={receipt.release_id}")
    print(f"tag={receipt.tag}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"source_environment={receipt.source_environment}")
    print(f"target_environment={receipt.target_environment}")
    print(f"bundle_fingerprint={receipt.bundle_fingerprint}")
    print(f"promotion_gate_fingerprint={receipt.promotion_gate_fingerprint}")
    print(f"verification_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
