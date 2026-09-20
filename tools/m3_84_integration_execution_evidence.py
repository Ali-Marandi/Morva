from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.integration_execution_evidence import (
    IntegrationExecutionEvidenceError,
    load_execution_evidence,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify Morva staging/pilot integration execution evidence"
    )
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--environment", required=True)
    args = parser.parse_args()

    try:
        receipt = load_execution_evidence(args.evidence)
        if receipt.repository != args.repository:
            raise IntegrationExecutionEvidenceError(
                "repository mismatch"
            )
        if receipt.candidate_sha.lower() != args.candidate_sha.lower():
            raise IntegrationExecutionEvidenceError(
                "candidate SHA mismatch"
            )
        if receipt.target_environment != args.environment:
            raise IntegrationExecutionEvidenceError(
                "target environment mismatch"
            )
    except (IntegrationExecutionEvidenceError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.84 execution evidence blocked: {exc}\n")

    print("M3.84 integration execution evidence verified")
    print(f"repository={receipt.repository}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"environment={receipt.target_environment}")
    print(f"execution_id={receipt.execution_id}")
    print(f"evidence_fingerprint={receipt.evidence_fingerprint}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
