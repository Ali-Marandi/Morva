from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.independent_release_lineage_verifier import (
    IndependentLineageVerificationError,
    verify_release_lineage,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify a Morva production release lineage"
    )
    parser.add_argument("--technical-readiness-gate", type=Path, required=True)
    parser.add_argument("--final-readiness-receipt", type=Path, required=True)
    parser.add_argument("--production-certification-receipt", type=Path, required=True)
    parser.add_argument("--external-registry", type=Path, required=True)
    parser.add_argument("--policy-receipt", type=Path, required=True)
    parser.add_argument("--lineage-manifest", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_release_lineage(
            technical_readiness_gate=args.technical_readiness_gate,
            final_readiness_receipt=args.final_readiness_receipt,
            production_certification_receipt=args.production_certification_receipt,
            external_registry=args.external_registry,
            policy_receipt=args.policy_receipt,
            lineage_manifest=args.lineage_manifest,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
        )
        write_receipt(receipt, args.output)
    except (
        IndependentLineageVerificationError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(2, f"M3.71 lineage verification blocked: {exc}\n")

    print("M3.71 production release lineage independently verified")
    print(f"repository={receipt.repository}")
    print(f"release_id={receipt.release_id}")
    print(f"tag={receipt.tag}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"lineage_fingerprint={receipt.lineage_fingerprint}")
    print(f"verification_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
