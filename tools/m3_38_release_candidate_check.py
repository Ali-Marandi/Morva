from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from morva.runtime.release_certification import CertificationSignoff, ReleaseCertification


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("signoff timestamps must be timezone-aware")
    return parsed


def load_certification(path: Path) -> ReleaseCertification:
    payload = json.loads(path.read_text(encoding="utf-8"))
    signoffs = tuple(
        CertificationSignoff(
            role=item["role"],
            signer=item["signer"],
            signed_at=_parse_datetime(item["signed_at"]),
            evidence_uri=item["evidence_uri"],
        )
        for item in payload.get("signoffs", ())
    )
    return ReleaseCertification(
        release_id=payload["release_id"],
        candidate_sha=payload["candidate_sha"],
        required_evidence=tuple(payload["required_evidence"]),
        verified_evidence=tuple(payload["verified_evidence"]),
        security_signoff_complete=bool(payload.get("security_signoff_complete", False)),
        disaster_recovery_signoff_complete=bool(
            payload.get("disaster_recovery_signoff_complete", False)
        ),
        load_signoff_complete=bool(payload.get("load_signoff_complete", False)),
        reconciliation_signoff_complete=bool(
            payload.get("reconciliation_signoff_complete", False)
        ),
        signoffs=signoffs,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Morva release certification evidence bundle")
    parser.add_argument("evidence_file", type=Path)
    parser.add_argument(
        "--expected-sha",
        default=os.getenv("GITHUB_SHA", ""),
        help="Expected Git commit SHA; defaults to GITHUB_SHA when present.",
    )
    args = parser.parse_args()

    certification = load_certification(args.evidence_file)
    if args.expected_sha and certification.candidate_sha.lower() != args.expected_sha.lower():
        raise SystemExit("candidate_sha does not match the expected release commit")

    certification.assert_release_ready()
    print(f"M3.38 release certification verified: {certification.release_id}")
    print(f"candidate_sha={certification.candidate_sha}")
    print(f"fingerprint={certification.fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
