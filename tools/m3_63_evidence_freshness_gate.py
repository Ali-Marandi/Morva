from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from morva.runtime.evidence_freshness_gate import (
    EvidenceFreshnessGateError,
    build_evidence_freshness_gate,
    write_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the Morva evidence-freshness gate"
    )
    parser.add_argument("--bundle-archive", type=Path, required=True)
    parser.add_argument("--bundle-metadata", type=Path, required=True)
    parser.add_argument("--promotion-gate", type=Path, required=True)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--deployment-attestation", type=Path, required=True)
    parser.add_argument("--release-receipt", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--checked-at", required=False)
    parser.add_argument("--max-release-age-hours", type=int, required=True)
    parser.add_argument("--max-approval-age-hours", type=int, required=True)
    parser.add_argument("--max-deployment-age-hours", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    checked_at = (
        datetime.fromisoformat(args.checked_at)
        if args.checked_at
        else datetime.now(timezone.utc)
    )

    try:
        gate = build_evidence_freshness_gate(
            bundle_archive=args.bundle_archive,
            bundle_metadata=args.bundle_metadata,
            promotion_gate=args.promotion_gate,
            authorization=args.authorization,
            deployment_attestation=args.deployment_attestation,
            release_receipt=args.release_receipt,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
            checked_at=checked_at,
            max_release_age_hours=args.max_release_age_hours,
            max_approval_age_hours=args.max_approval_age_hours,
            max_deployment_age_hours=args.max_deployment_age_hours,
        )
        write_gate(gate, args.output)
    except (EvidenceFreshnessGateError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.63 freshness gate blocked: {exc}\n")

    print("M3.63 evidence freshness gate verified")
    print(f"repository={gate.repository}")
    print(f"release_id={gate.release_id}")
    print(f"tag={gate.tag}")
    print(f"candidate_sha={gate.candidate_sha}")
    print(f"checked_at={gate.checked_at.isoformat()}")
    print(f"fingerprint={gate.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
