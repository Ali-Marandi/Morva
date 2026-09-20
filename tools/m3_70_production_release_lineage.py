from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from morva.runtime.production_release_lineage import (
    ReleaseLineageError,
    build_release_lineage,
    write_lineage,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a Morva production release lineage manifest"
    )
    parser.add_argument(
        "--technical-readiness-gate",
        type=Path,
        required=True,
    )
    parser.add_argument("--final-readiness-receipt", type=Path, required=True)
    parser.add_argument(
        "--production-certification-receipt",
        type=Path,
        required=True,
    )
    parser.add_argument("--external-registry", type=Path, required=True)
    parser.add_argument("--policy-receipt", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--verified-at")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        verified_at = (
            datetime.fromisoformat(args.verified_at)
            if args.verified_at
            else datetime.now(timezone.utc)
        )
        lineage = build_release_lineage(
            technical_readiness_gate=args.technical_readiness_gate,
            final_readiness_receipt=args.final_readiness_receipt,
            production_certification_receipt=args.production_certification_receipt,
            external_registry=args.external_registry,
            policy_receipt=args.policy_receipt,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
            verified_at=verified_at,
        )
        write_lineage(lineage, args.output)
    except (ReleaseLineageError, OSError, ValueError) as exc:
        parser.exit(
            2,
            f"M3.70 release lineage blocked: {exc}\n",
        )

    print("M3.70 production release lineage verified")
    print(f"repository={lineage.repository}")
    print(f"release_id={lineage.release_id}")
    print(f"tag={lineage.tag}")
    print(f"candidate_sha={lineage.candidate_sha}")
    print(f"lineage_fingerprint={lineage.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
