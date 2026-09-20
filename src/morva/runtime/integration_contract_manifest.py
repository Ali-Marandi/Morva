from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path


class IntegrationContractManifestError(ValueError):
    """Raised when the integration contract manifest is invalid."""


ADAPTER_OPERATIONS = {
    "sina": ("publish_order", "publish_payslip", "health"),
    "accounting": ("post_payroll_batch", "health"),
    "treasury": ("submit_payment_batch", "health"),
    "bank": ("submit_payment_batch", "reconcile", "health"),
    "tax": ("submit_payroll_tax", "health"),
    "insurance": ("submit_payroll_contribution", "health"),
}


@dataclass(frozen=True, slots=True)
class IntegrationContractManifest:
    manifest_version: int
    repository: str
    candidate_sha: str
    payload_schema_version: str
    adapters: tuple[str, ...]
    created_at: str

    def __post_init__(self) -> None:
        if self.manifest_version != 1:
            raise IntegrationContractManifestError(
                "unsupported integration manifest version"
            )
        if not self.repository.strip():
            raise IntegrationContractManifestError(
                "repository is required"
            )
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef"
            for char in self.candidate_sha.lower()
        ):
            raise IntegrationContractManifestError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if not self.payload_schema_version.strip():
            raise IntegrationContractManifestError(
                "payload_schema_version is required"
            )
        if tuple(self.adapters) != tuple(ADAPTER_OPERATIONS):
            raise IntegrationContractManifestError(
                "adapter set must use canonical order"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "manifest_version": self.manifest_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "payload_schema_version": self.payload_schema_version,
            "adapters": [
                {
                    "name": adapter,
                    "operations": list(ADAPTER_OPERATIONS[adapter]),
                    "requires_idempotency_key": True,
                    "requires_correlation_id": True,
                }
                for adapter in self.adapters
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
            "manifest_version": self.manifest_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "payload_schema_version": self.payload_schema_version,
            "adapters": [
                {
                    "name": adapter,
                    "operations": list(ADAPTER_OPERATIONS[adapter]),
                    "requires_idempotency_key": True,
                    "requires_correlation_id": True,
                }
                for adapter in self.adapters
            ],
            "created_at": self.created_at,
            "fingerprint": self.fingerprint,
        }


def build_manifest(
    *,
    repository: str,
    candidate_sha: str,
    payload_schema_version: str = "1",
    created_at: str,
) -> IntegrationContractManifest:
    return IntegrationContractManifest(
        manifest_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        payload_schema_version=payload_schema_version,
        adapters=tuple(ADAPTER_OPERATIONS),
        created_at=created_at,
    )


def write_manifest(
    manifest: IntegrationContractManifest,
    path: Path,
) -> None:
    if path.exists():
        raise IntegrationContractManifestError(
            "integration contract manifest is write-once"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            manifest.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def load_manifest(path: Path) -> IntegrationContractManifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        adapter_items = tuple(payload["adapters"])
        adapters = tuple(item["name"] for item in adapter_items)
        if any(
            tuple(item["operations"]) != ADAPTER_OPERATIONS[item["name"]]
            or item["requires_idempotency_key"] is not True
            or item["requires_correlation_id"] is not True
            for item in adapter_items
        ):
            raise IntegrationContractManifestError(
                "adapter operation contract mismatch"
            )
        manifest = IntegrationContractManifest(
            manifest_version=int(payload["manifest_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            payload_schema_version=payload["payload_schema_version"],
            adapters=adapters,
            created_at=payload["created_at"],
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        if isinstance(exc, IntegrationContractManifestError):
            raise
        raise IntegrationContractManifestError(
            "integration contract manifest structure is invalid"
        ) from exc
    if payload.get("fingerprint") != manifest.fingerprint:
        raise IntegrationContractManifestError(
            "integration contract manifest fingerprint mismatch"
        )
    return manifest
