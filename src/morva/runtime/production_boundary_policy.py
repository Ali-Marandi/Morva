from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


class ProductionBoundaryPolicyError(ValueError):
    """Raised when a production-boundary policy check fails."""


FORBIDDEN_COMMANDS = (
    "gh release create",
    "gh release edit",
    "gh release delete",
    "gh release upload",
    "git push",
    "git tag ",
    "kubectl apply",
    "kubectl delete",
    "helm install",
    "helm upgrade",
    "helm rollback",
    "terraform apply",
    "terraform destroy",
)
PRIVATE_MARKERS = (
    b"BEGIN PRIVATE KEY",
    b"BEGIN OPENSSH PRIVATE KEY",
    b"BEGIN RSA PRIVATE KEY",
    b"BEGIN EC PRIVATE KEY",
)
CREDENTIAL_MARKERS = (
    b"ghp_",
    b"github_pat_",
    b"AWS_SECRET_ACCESS_KEY",
)


@dataclass(frozen=True, slots=True)
class PolicyFinding:
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
class ProductionBoundaryPolicyReceipt:
    policy_version: int
    repository: str
    scanned_paths: tuple[str, ...]
    findings: tuple[PolicyFinding, ...]
    verified_at: datetime

    def __post_init__(self) -> None:
        if self.policy_version != 1:
            raise ProductionBoundaryPolicyError(
                "unsupported policy version"
            )
        if not self.repository.strip():
            raise ProductionBoundaryPolicyError(
                "repository is required"
            )
        if not self.scanned_paths:
            raise ProductionBoundaryPolicyError(
                "scanned_paths cannot be empty"
            )
        if self.verified_at.tzinfo is None:
            raise ProductionBoundaryPolicyError(
                "verified_at must be timezone-aware"
            )

    @property
    def passed(self) -> bool:
        return not self.findings

    @property
    def fingerprint(self) -> str:
        payload = {
            "policy_version": self.policy_version,
            "repository": self.repository,
            "scanned_paths": list(self.scanned_paths),
            "findings": [
                finding.to_payload()
                for finding in self.findings
            ],
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "repository": self.repository,
            "scanned_paths": list(self.scanned_paths),
            "findings": [
                finding.to_payload()
                for finding in self.findings
            ],
            "passed": self.passed,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def scan_repository(
    *,
    root: Path,
    repository: str,
    relative_paths: tuple[str, ...],
) -> ProductionBoundaryPolicyReceipt:
    paths = tuple(sorted(set(relative_paths)))
    if not paths:
        raise ProductionBoundaryPolicyError(
            "at least one path must be scanned"
        )

    findings: list[PolicyFinding] = []
    for relative in paths:
        path = root / relative
        try:
            data = path.read_bytes()
        except OSError as exc:
            findings.append(
                PolicyFinding(
                    path=relative,
                    rule="readable",
                    detail=str(exc),
                )
            )
            continue

        for marker in PRIVATE_MARKERS:
            if marker in data:
                findings.append(
                    PolicyFinding(
                        path=relative,
                        rule="private-key-material",
                        detail=marker.decode("ascii"),
                    )
                )
        for marker in CREDENTIAL_MARKERS:
            if marker in data:
                findings.append(
                    PolicyFinding(
                        path=relative,
                        rule="credential-material",
                        detail=marker.decode("ascii"),
                    )
                )

        text = data.decode("utf-8", errors="replace")
        if relative.startswith(".github/workflows/"):
            for command in FORBIDDEN_COMMANDS:
                for line in text.splitlines():
                    if command in line:
                        findings.append(
                            PolicyFinding(
                                path=relative,
                                rule="workflow-mutation",
                                detail=command,
                            )
                        )
                        break
            if "permissions:\n  contents: write" in text:
                findings.append(
                    PolicyFinding(
                        path=relative,
                        rule="workflow-write-permission",
                        detail="contents: write",
                    )
                )

    return ProductionBoundaryPolicyReceipt(
        policy_version=1,
        repository=repository,
        scanned_paths=paths,
        findings=tuple(findings),
        verified_at=datetime.now(timezone.utc),
    )


def write_receipt(
    receipt: ProductionBoundaryPolicyReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise ProductionBoundaryPolicyError(
            "policy receipt is write-once"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            receipt.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if not receipt.passed:
        raise ProductionBoundaryPolicyError(
            "production-boundary policy failed"
        )
