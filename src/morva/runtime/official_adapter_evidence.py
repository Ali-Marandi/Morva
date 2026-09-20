from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path


class OfficialAdapterEvidenceError(ValueError):
    """Raised when official-adapter evidence is incomplete or inconsistent."""


REQUIRED_ADAPTERS = (
    "sina",
    "accounting",
    "treasury",
    "bank",
    "tax",
    "insurance",
)


@dataclass(frozen=True, slots=True)
class AdapterEvidence:
    evidence_version: int
    adapter: str
    provider: str
    repository: str
    candidate_sha: str
    schema_version: str
    contract_source: str
    digest_sha256: str
    verified_at: str
    expires_at: str | None = None

    def __post_init__(self) -> None:
        if self.evidence_version != 1:
            raise OfficialAdapterEvidenceError(
                "unsupported adapter evidence version"
            )
        if self.adapter not in REQUIRED_ADAPTERS:
            raise OfficialAdapterEvidenceError("unsupported adapter role")
        if (
            not self.provider.strip()
            or not self.repository.strip()
            or not self.schema_version.strip()
            or not self.contract_source.strip()
        ):
            raise OfficialAdapterEvidenceError(
                "provider, repository, schema_version and contract_source are required"
            )
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef"
            for char in self.candidate_sha.lower()
        ):
            raise OfficialAdapterEvidenceError(
                "candidate_sha must be a Git commit SHA-1"
            )
        if len(self.digest_sha256) != 64 or any(
            char not in "0123456789abcdef"
            for char in self.digest_sha256.lower()
        ):
            raise OfficialAdapterEvidenceError(
                "digest_sha256 must be a SHA-256 hex digest"
            )
        for name, value in (
            ("verified_at", self.verified_at),
            ("expires_at", self.expires_at),
        ):
            if value is None:
                continue
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError as exc:
                raise OfficialAdapterEvidenceError(
                    f"{name} must be ISO-8601"
                ) from exc
            if parsed.tzinfo is None:
                raise OfficialAdapterEvidenceError(
                    f"{name} must include a timezone"
                )


@dataclass(frozen=True, slots=True)
class OfficialAdapterEvidenceRegistry:
    registry_version: int
    repository: str
    candidate_sha: str
    items: tuple[AdapterEvidence, ...]
    registered_at: datetime

    def __post_init__(self) -> None:
        if self.registry_version != 1:
            raise OfficialAdapterEvidenceError(
                "unsupported adapter registry version"
            )
        if not self.repository.strip():
            raise OfficialAdapterEvidenceError("repository is required")
        if len(self.items) != len(REQUIRED_ADAPTERS):
            raise OfficialAdapterEvidenceError(
                "complete official-adapter evidence is required"
            )
        if self.registered_at.tzinfo is None:
            raise OfficialAdapterEvidenceError(
                "registered_at must be timezone-aware"
            )
        if tuple(item.adapter for item in self.items) != REQUIRED_ADAPTERS:
            raise OfficialAdapterEvidenceError(
                "adapter evidence must use the canonical adapter order"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "registry_version": self.registry_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "items": [
                {
                    "adapter": item.adapter,
                    "provider": item.provider,
                    "schema_version": item.schema_version,
                    "contract_source": item.contract_source,
                    "digest_sha256": item.digest_sha256.lower(),
                    "verified_at": item.verified_at,
                    "expires_at": item.expires_at,
                }
                for item in self.items
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
            "registry_version": self.registry_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "items": [
                {
                    "evidence_version": item.evidence_version,
                    "adapter": item.adapter,
                    "provider": item.provider,
                    "repository": item.repository,
                    "candidate_sha": item.candidate_sha,
                    "schema_version": item.schema_version,
                    "contract_source": item.contract_source,
                    "digest_sha256": item.digest_sha256,
                    "verified_at": item.verified_at,
                    "expires_at": item.expires_at,
                }
                for item in self.items
            ],
            "registered_at": self.registered_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def build_registry(
    items: tuple[AdapterEvidence, ...],
    *,
    repository: str,
    candidate_sha: str,
    checked_at: datetime,
) -> OfficialAdapterEvidenceRegistry:
    if checked_at.tzinfo is None:
        raise OfficialAdapterEvidenceError(
            "checked_at must be timezone-aware"
        )
    if tuple(item.adapter for item in items) != REQUIRED_ADAPTERS:
        raise OfficialAdapterEvidenceError(
            "adapter evidence does not cover all required adapters in canonical order"
        )
    now = checked_at.astimezone(timezone.utc)
    for item in items:
        if item.repository != repository:
            raise OfficialAdapterEvidenceError(
                f"repository mismatch for adapter {item.adapter}"
            )
        if item.candidate_sha.lower() != candidate_sha.lower():
            raise OfficialAdapterEvidenceError(
                f"candidate SHA mismatch for adapter {item.adapter}"
            )
        if datetime.fromisoformat(item.verified_at) > now:
            raise OfficialAdapterEvidenceError(
                f"verification timestamp is in the future for adapter {item.adapter}"
            )
        if item.expires_at is not None and datetime.fromisoformat(
            item.expires_at
        ) <= now:
            raise OfficialAdapterEvidenceError(
                f"adapter evidence is expired for {item.adapter}"
            )
    return OfficialAdapterEvidenceRegistry(
        registry_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        items=items,
        registered_at=checked_at,
    )


def assert_activation_ready(
    registry: OfficialAdapterEvidenceRegistry,
    *,
    repository: str,
    candidate_sha: str,
    checked_at: datetime,
) -> None:
    if registry.repository != repository:
        raise OfficialAdapterEvidenceError("adapter registry repository mismatch")
    if registry.candidate_sha.lower() != candidate_sha.lower():
        raise OfficialAdapterEvidenceError(
            "adapter registry candidate SHA mismatch"
        )
    if checked_at.tzinfo is None:
        raise OfficialAdapterEvidenceError(
            "activation check time must be timezone-aware"
        )
    now = checked_at.astimezone(timezone.utc)
    if tuple(item.adapter for item in registry.items) != REQUIRED_ADAPTERS:
        raise OfficialAdapterEvidenceError("adapter registry is incomplete")
    for item in registry.items:
        if datetime.fromisoformat(item.verified_at) > now:
            raise OfficialAdapterEvidenceError(
                f"adapter evidence is future-dated for {item.adapter}"
            )
        if item.expires_at is not None and datetime.fromisoformat(
            item.expires_at
        ) <= now:
            raise OfficialAdapterEvidenceError(
                f"adapter evidence is expired for {item.adapter}"
            )


def load_registry(path: Path) -> OfficialAdapterEvidenceRegistry:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        items = tuple(
            AdapterEvidence(
                evidence_version=int(item["evidence_version"]),
                adapter=item["adapter"],
                provider=item["provider"],
                repository=item["repository"],
                candidate_sha=item["candidate_sha"],
                schema_version=item["schema_version"],
                contract_source=item["contract_source"],
                digest_sha256=item["digest_sha256"],
                verified_at=item["verified_at"],
                expires_at=item.get("expires_at"),
            )
            for item in payload["items"]
        )
        registry = OfficialAdapterEvidenceRegistry(
            registry_version=int(payload["registry_version"]),
            repository=payload["repository"],
            candidate_sha=payload["candidate_sha"],
            items=items,
            registered_at=datetime.fromisoformat(payload["registered_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise OfficialAdapterEvidenceError(
            "official adapter evidence registry structure is invalid"
        ) from exc
    if payload.get("fingerprint") != registry.fingerprint:
        raise OfficialAdapterEvidenceError(
            "official adapter evidence registry fingerprint mismatch"
        )
    return registry


def write_registry(
    registry: OfficialAdapterEvidenceRegistry,
    path: Path,
) -> None:
    if path.exists():
        raise OfficialAdapterEvidenceError(
            "official adapter evidence registry is write-once"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            registry.to_payload(),
            ensure_ascii=True,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
