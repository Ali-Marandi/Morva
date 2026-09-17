from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (ROOT / "src", ROOT / "tests", ROOT / "tools", ROOT / "ops")

PATTERNS = (
    ("private_key", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
)


def iter_text_files() -> list[Path]:
    files: set[Path] = set()
    for root in SCAN_ROOTS:
        if root.exists():
            files.update(path for path in root.rglob("*") if path.is_file())
    return sorted(path for path in files if path.suffix not in {".pyc", ".db"})


def find_high_confidence_secrets() -> list[str]:
    findings: list[str] = []
    for path in iter_text_files():
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for name, pattern in PATTERNS:
                if pattern.search(line):
                    findings.append(f"{path.relative_to(ROOT)}:{line_number}: {name}")
    return findings


def main() -> int:
    findings = find_high_confidence_secrets()
    if findings:
        print("M3.36 security preflight failed: high-confidence secret material detected.")
        for finding in findings:
            print(f"- {finding}")
        return 1

    print(
        "M3.36 security preflight passed: no high-confidence private-key/token signatures "
        "were found in source, tests, tools or operational scripts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
