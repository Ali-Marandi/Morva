from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from morva.runtime.external_certification_evidence import (
    ExternalCertificationEvidenceError,
    ExternalCertificationEvidenceRegistry,
    build_evidence_registry,
    write_registry,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Register Morva external certification evidence"
    )
    parser.add_argument("--repository", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("evidence", nargs="+", type=Path)
    args = parser.parse_args()

    try:
        items = build_evidence_registry(
            tuple(args.evidence),
            repository=args.repository,
            candidate_sha=args.candidate_sha,
        )
        registry = ExternalCertificationEvidenceRegistry(
            registry_version=1,
            repository=args.repository,
            candidate_sha=args.candidate_sha,
            items=items,
            registered_at=datetime.now(timezone.utc),
        )
        write_registry(registry, args.output)
    except (ExternalCertificationEvidenceError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.66 external evidence blocked: {exc}\n")

    print("M3.66 external certification evidence registry verified")
    print(f"repository={registry.repository}")
    print(f"candidate_sha={registry.candidate_sha}")
    print(f"roles={len(registry.items)}")
    print(f"fingerprint={registry.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
