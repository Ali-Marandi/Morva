from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.official_adapter_evidence import REQUIRED_ADAPTERS


class IntegrationExecutionEvidenceError(ValueError):
    """Raised when staging/pilot integration execution evidence is invalid."""


@dataclass(frozen=True, slots=True)
class AdapterExecutionEvidence:
    adapter: str
    environment: str
    status: str
    evidence_id: str
    evidence_sha256: str
    started_at: str
    finished_at: str
    operator: str

    def __post_init__(self) -> None:
        if self.adapter not in REQUIRED_ADAPTERS:
            raise IntegrationExecutionEvidenceError(
                "unsupported adapter in execution evidence"
            )
        if self.environment not in {"staging", "pilot"}:
            raise IntegrationExecutionEvidenceError(
                "execution environment must be staging or pilot"
            )
        if self.status != "passed":
            raise IntegrationExecutionEvidenceError(
                "adapter execution status must be passed"
            )
        if not self.evidence_id.strip() or not self.operator.strip():
            raise IntegrationExecutionEvidenceError(
                "evidence_id and operator are required"
            )
        if len(self.evidence_sha256) != 64 or any(
            char not in "0123456789abcdef"
            for char in self.evidence_sha256.lower()
        ):
            raise IntegrationExecutionEvidenceError(
                "evidence_sha256 must be SHA-256"
            )
        try:
            started = datetime.fromisoformat(self.started_at)
            finished = datetime.fromisoformat(self.finished_at)
        except ValueError as exc:
            raise IntegrationExecutionEvidenceError(
                "execution timestamps must be ISO-8601"
            ) from exc
        if started.tzinfo is None or finished.tzinfo is None:
            raise IntegrationExecutionEvidenceError(
                "execution timestamps must include a timezone"
            )
        if finished < started:
            raise IntegrationExecutionEvidenceError(
                "finished_at cannot precede started_at"
            )

    def to_payload(self) -> dict[str, str]:
        return {
            "adapter": self.adapter,
            "environment": self.environment,
            "status": self.status,
            "evidence_id": self.evidence_id,
            "evidence_sha256": self.evidence_sha256.lower(),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "operator": self.operator,
        }


@dataclass(frozen=True, slots=True)
class IntegrationExecutionEvidenceReceipt:
    evidence_version: int
    repository: str
    candidate_sha: str
    target_environment: str
    execution_id: str
    evidence_items: tuple[AdapterExecutionEvidence, ...]
    checked_at: datetime

    def __post_init__(self) -> None:
        if self.evidence_version != 1:
            raise IntegrationExecutionEvidenceError(
                "unsupported execution evidence version"
            )
        if not self.repository.strip() or not self.execution_id.strip():
            raise IntegrationExecutionEvidenceError(
                "repository and execution_id are required"
            )
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef"
            for char in self.candidate_sha.lower()
        ):
            raise IntegrationExecutionEvidenceError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if self.target_environment not in {"staging", "pilot"}:
            raise IntegrationExecutionEvidenceError(
                "target_environment must be staging or pilot"
            )
        if tuple(item.adapter for item in self.evidence_items) != REQUIRED_ADAPTERS:
            raise IntegrationExecutionEvidenceError(
                "execution evidence must cover the canonical adapter set in order"
            )
        if self.checked_at.tzinfo is None:
            raise IntegrationExecutionEvidenceError(
                "checked_at must be timezone-aware"
            )
        checked = self.checked_at
        for item in self.evidence_items:
            if item.environment != self.target_environment:
                raise IntegrationExecutionEvidenceError(
                    f"adapter environment mismatch for {item.adapter}"
                )
            if datetime.fromisoformat(item.finished_at) > checked:
                raise IntegrationExecutionEvidenceError(
                    f"adapter evidence is future-dated for {item.adapter}"
                )

    @property
    def evidence_fingerprint(self) -> str:
        payload = {
            "evidence_version": self.evidence_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "target_environment": self.target_environment,
            "execution_id": self.execution_id,
            "evidence_items": [
                item.to_payload() for item in self.evidence_items
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
            "evidence_version": self.evidence_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "target_environment": self.target_environment,
            "execution_id": self.execution_id,
            "evidence_items": [
                item.to_payload() for item in self.evidence_items
            ],
            "checked_at": self.checked_at.isoformat(),
            "evidence_fingerprint": self.evidence_fingerprint,
        }


def load_execution_evidence(path: Path) -> IntegrationExecutionEvidenceReceipt:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = tuple(
            AdapterExecutionEvidence(
                adapter=item["adapter"],
                environment=item["environment"],
                status=item["status"],
                evidence_id=item["evidence_id"],
                evidence_sha256=item["evidence_sha256"],
                started_at=item["started_at"],
                finished_at=item["finished_at"],
                operator=item["operator"],
            )
            for item in payload["evidence_items"]
        )
        receipt = IntegrationExecutionEvidenceReceipt(
            evidence_version=int(payload["evidence_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            target_environment=payload["target_environment"],
            execution_id=payload["execution_id"],
            evidence_items=items,
            checked_at=datetime.fromisoformat(payload["checked_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise IntegrationExecutionEvidenceError(
            "execution evidence receipt structure is invalid"
        ) from exc
    if payload.get("evidence_fingerprint") != receipt.evidence_fingerprint:
        raise IntegrationExecutionEvidenceError(
            "execution evidence fingerprint mismatch"
        )
    return receipt


def write_execution_evidence(
    receipt: IntegrationExecutionEvidenceReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise IntegrationExecutionEvidenceError(
            "execution evidence receipt is write-once"
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
