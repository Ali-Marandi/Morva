from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re


class CIWorkflowIntegrityError(ValueError):
    """Raised when a GitHub Actions workflow violates the integrity contract."""


ALLOWED_UNSCOPED_PUSH = {
    ".github/workflows/ci.yml",
    ".github/workflows/backend-security.yml",
    ".github/workflows/web-typecheck.yml",
    ".github/workflows/web-pages.yml",
}

FORBIDDEN_MUTATIONS = (
    "gh release create",
    "gh release edit",
    "gh release delete",
    "gh release upload",
    "git push",
    "git tag",
    "kubectl apply",
    "kubectl delete",
    "helm install",
    "helm upgrade",
    "helm rollback",
    "terraform apply",
    "terraform destroy",
)

FORBIDDEN_DYNAMIC_EXECUTION = (
    "eval ",
    "bash -c",
    "sh -c",
)


@dataclass(frozen=True, slots=True)
class WorkflowIntegrityFinding:
    path: str
    rule: str
    detail: str

    def to_payload(self) -> dict[str, str]:
        return {
            "path": self.path,
            "rule": self.rule,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class CIWorkflowIntegrityReceipt:
    verifier_version: int
    repository: str
    scanned_paths: tuple[str, ...]
    findings: tuple[WorkflowIntegrityFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "scanned_paths": list(self.scanned_paths),
            "findings": [
                finding.to_payload() for finding in self.findings
            ],
        }
        return sha256(
            json.dumps(
                payload,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "scanned_paths": list(self.scanned_paths),
            "findings": [
                finding.to_payload() for finding in self.findings
            ],
            "passed": self.passed,
            "fingerprint": self.fingerprint,
        }


def _top_level_key(text: str, key: str) -> bool:
    return re.search(rf"(?m)^{re.escape(key)}:\s*$", text) is not None


def _has_jobs(text: str) -> bool:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "jobs:" or line[: len(line) - len(line.lstrip())]:
            continue
        for child in lines[index + 1 :]:
            if not child.strip() or child.lstrip().startswith("#"):
                continue
            if len(child) - len(child.lstrip()) == 0:
                return False
            return True
    return False


def _push_block(text: str) -> str | None:
    lines = text.splitlines()
    on_index = next(
        (
            i
            for i, line in enumerate(lines)
            if line.strip() == "on:" and not line.startswith(" ")
        ),
        None,
    )
    if on_index is None:
        return None
    block: list[str] = []
    for line in lines[on_index + 1 :]:
        if line and not line.startswith(" ") and not line.startswith("	"):
            break
        block.append(line)
    push_index = next(
        (
            i
            for i, line in enumerate(block)
            if line.strip() == "push:" and line.startswith("  ")
        ),
        None,
    )
    if push_index is None:
        return None
    push_indent = len(block[push_index]) - len(block[push_index].lstrip())
    push_lines: list[str] = []
    for line in block[push_index + 1 :]:
        if line.strip() and not line.startswith(" " * (push_indent + 1)):
            break
        push_lines.append(line)
    return "\n".join(push_lines)


def _has_main_branch(push_block: str) -> bool:
    if re.search(r"(?m)^\s+branches:\s*\[.*\bmain\b.*\]\s*$", push_block):
        return True
    if re.search(r"(?m)^\s+-\s+main\s*$", push_block):
        return True
    if re.search(r"(?m)^\s+branches:\s*$", push_block):
        return bool(re.search(r"(?m)^\s+-\s+main\s*$", push_block))
    return False


def _dynamic_execution_findings(path: str, text: str) -> list[WorkflowIntegrityFinding]:
    findings: list[WorkflowIntegrityFinding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        candidate = _shell_code_without_literals(stripped)
        for command in FORBIDDEN_DYNAMIC_EXECUTION:
            if re.search(rf"(?<![\w-]){re.escape(command.strip())}(?:\s|$)", candidate):
                findings.append(
                    WorkflowIntegrityFinding(
                        path=path,
                        rule="workflow-dynamic-execution",
                        detail=f"{command.strip()} at line {number}",
                    )
                )
    return findings


def _shell_code_without_literals(line: str) -> str:
    output: list[str] = []
    quote: str | None = None
    escaped = False
    for char in line:
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", "\""}:
            quote = char
            continue
        if char == "#":
            break
        output.append(char)
    return "".join(output)


def _mutation_findings(path: str, text: str) -> list[WorkflowIntegrityFinding]:
    findings: list[WorkflowIntegrityFinding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        candidate = re.sub(r"^-\s*run:\s*", "", stripped)
        candidate = _shell_code_without_literals(candidate)
        for command in FORBIDDEN_MUTATIONS:
            if re.search(rf"(?<![\w-]){re.escape(command)}(?![\w-])", candidate):
                findings.append(
                    WorkflowIntegrityFinding(
                        path=path,
                        rule="workflow-mutation",
                        detail=f"{command} at line {number}",
                    )
                )
    return findings


def scan_workflows(root: Path, repository: str) -> CIWorkflowIntegrityReceipt:
    workflow_root = root / ".github" / "workflows"
    if not workflow_root.is_dir():
        raise CIWorkflowIntegrityError("workflow directory does not exist")

    paths = tuple(
        sorted(
            str(path.relative_to(root))
            for path in workflow_root.iterdir()
            if path.is_file() and path.suffix in {".yml", ".yaml"}
        )
    )
    if not paths:
        raise CIWorkflowIntegrityError("no workflow files found")

    findings: list[WorkflowIntegrityFinding] = []
    for relative in paths:
        path = root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                WorkflowIntegrityFinding(relative, "readable", str(exc))
            )
            continue

        if not _top_level_key(text, "name"):
            findings.append(
                WorkflowIntegrityFinding(relative, "workflow-name", "top-level name is required")
            )
        if not _top_level_key(text, "on"):
            findings.append(
                WorkflowIntegrityFinding(relative, "workflow-trigger", "top-level on is required")
            )
        if not _has_jobs(text):
            findings.append(
                WorkflowIntegrityFinding(
                    relative,
                    "workflow-jobs",
                    "at least one top-level job is required",
                )
            )

        push = _push_block(text)
        if push is not None and _has_main_branch(push):
            if relative not in ALLOWED_UNSCOPED_PUSH and not re.search(
                r"(?m)^\s+paths:\s*$", push
            ):
                findings.append(
                    WorkflowIntegrityFinding(
                        relative,
                        "push-path-scope",
                        "main push workflows must define paths",
                    )
                )

        if re.search(r"(?m)^\s+contents:\s*write\s*$", text):
            findings.append(
                WorkflowIntegrityFinding(
                    relative,
                    "contents-write",
                    "contents: write is forbidden by the CI integrity contract",
                )
            )

        findings.extend(_dynamic_execution_findings(relative, text))
        findings.extend(_mutation_findings(relative, text))

    return CIWorkflowIntegrityReceipt(
        verifier_version=1,
        repository=repository,
        scanned_paths=paths,
        findings=tuple(findings),
    )


def write_receipt(receipt: CIWorkflowIntegrityReceipt, path: Path) -> None:
    if path.exists():
        raise CIWorkflowIntegrityError("workflow integrity receipt is write-once")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt.to_payload(), ensure_ascii=True, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    if not receipt.passed:
        raise CIWorkflowIntegrityError("CI workflow integrity check failed")
