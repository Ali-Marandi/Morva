from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.independent_certification_verifier import (
    IndependentCertificationVerificationError,
    verify_production_certification,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Independently verify Morva production certification"
    )
    parser.add_argument("--final-technical-gate", type=Path, required=True)
    parser.add_argument("--final-freshness-gate", type=Path, required=True)
    parser.add_argument("--final-gate", type=Path, required=True)
    parser.add_argument("--external-registry", type=Path, required=True)
    parser.add_argument("--certification-gate", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_production_certification(
            final_technical_gate=args.final_technical_gate,
            final_freshness_gate=args.final_freshness_gate,
            final_gate=args.final_gate,
            external_registry=args.external_registry,
            certification_gate=args.certification_gate,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
        )
        write_receipt(receipt, args.output)
    except (
        IndependentCertificationVerificationError,
        OSError,
        ValueError,
    ) as exc:
        parser.exit(2, f"M3.68 certification verification blocked: {exc}\n")

    print("M3.68 production certification independently verified")
    print(f"repository={receipt.repository}")
    print(f"release_id={receipt.release_id}")
    print(f"tag={receipt.tag}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(
        "certification_gate_fingerprint="
        f"{receipt.certification_gate_fingerprint}"
    )
    print(f"verification_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
