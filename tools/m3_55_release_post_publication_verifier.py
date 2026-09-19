from __future__ import annotations

import argparse
from pathlib import Path

from morva.runtime.release_post_publication import (
    ReleasePostPublicationError,
    verify_published_release,
    write_receipt,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the integrity of a published Morva GitHub Release"
    )
    parser.add_argument("--gate", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        receipt = verify_published_release(
            gate_file=args.gate,
            archive_path=args.archive,
            artifact_metadata=args.metadata,
            repository=args.repository,
            tag=args.tag,
            candidate_sha=args.candidate_sha,
        )
        write_receipt(receipt, args.output)
    except (ReleasePostPublicationError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.55 post-publication verification blocked: {exc}\n")

    print("M3.55 published-release integrity verified")
    print(f"repository={receipt.repository}")
    print(f"release_id={receipt.release_id}")
    print(f"tag={receipt.tag}")
    print(f"candidate_sha={receipt.candidate_sha}")
    print(f"github_release_id={receipt.github_release_id}")
    print(f"gate_fingerprint={receipt.gate_fingerprint}")
    print(f"artifact_id={receipt.artifact_id}")
    print(f"artifact_fingerprint={receipt.artifact_fingerprint}")
    print(f"archive_sha256={receipt.archive_sha256}")
    print(f"receipt_fingerprint={receipt.fingerprint}")
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
