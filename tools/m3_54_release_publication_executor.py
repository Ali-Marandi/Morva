from __future__ import annotations

import argparse
import json
from pathlib import Path

from morva.runtime.release_publication_executor import (
    ReleasePublicationExecutorError,
    execute_publication,
    prepare_publication,
)


def _write_plan(plan, path: Path) -> None:
    payload = {
        "repository": plan.repository,
        "release_id": plan.release_id,
        "tag": plan.tag,
        "candidate_sha": plan.candidate_sha,
        "gate_fingerprint": plan.gate_fingerprint,
        "archive_sha256": plan.archive_sha256,
        "archive_path": plan.archive_path,
        "gate_path": plan.gate_path,
        "artifact_metadata_path": plan.artifact_metadata_path,
        "command": list(plan.command()),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely prepare or execute a Morva GitHub Release publication"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    common = {
        "gate": ("--gate", {"type": Path, "required": True}),
        "archive": ("--archive", {"type": Path, "required": True}),
        "metadata": ("--metadata", {"type": Path, "required": True}),
        "repository": ("--repository", {"required": True}),
        "tag": ("--tag", {"required": True}),
        "candidate_sha": ("--candidate-sha", {"required": True}),
    }
    prepare = subparsers.add_parser("prepare")
    for _, (flag, kwargs) in common.items():
        prepare.add_argument(flag, **kwargs)
    prepare.add_argument("--output", type=Path)

    publish = subparsers.add_parser("publish")
    for _, (flag, kwargs) in common.items():
        publish.add_argument(flag, **kwargs)
    publish.add_argument("--authorization", type=Path, required=True)

    args = parser.parse_args()
    common_kwargs = {
        "gate_file": args.gate,
        "archive_path": args.archive,
        "artifact_metadata": args.metadata,
        "repository": args.repository,
        "tag": args.tag,
        "candidate_sha": args.candidate_sha,
    }
    try:
        if args.command == "prepare":
            plan = prepare_publication(**common_kwargs)
            if args.output:
                _write_plan(plan, args.output)
            print("M3.54 release publication plan verified")
        else:
            plan = execute_publication(
                authorization_file=args.authorization,
                **common_kwargs,
            )
            print("M3.54 GitHub Release publication completed")
        print(f"repository={plan.repository}")
        print(f"release_id={plan.release_id}")
        print(f"tag={plan.tag}")
        print(f"candidate_sha={plan.candidate_sha}")
        print(f"gate_fingerprint={plan.gate_fingerprint}")
        print(f"archive_sha256={plan.archive_sha256}")
        print("command=" + " ".join(plan.command()))
        return 0
    except (ReleasePublicationExecutorError, OSError, ValueError) as exc:
        parser.exit(2, f"M3.54 publication blocked: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())