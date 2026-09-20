from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.official_adapter_evidence import (
    REQUIRED_ADAPTERS,
    OfficialAdapterEvidenceError,
    OfficialAdapterEvidenceRegistry,
    load_registry,
    assert_activation_ready,
)


class IndependentAdapterEvidenceVerificationError(ValueError):
    """Raised when official adapter evidence fails independent verification."""


@dataclass(frozen=True, slots=True)
class IndependentAdapterEvidenceReceipt:
    verifier_version: int
    repository: str
    candidate_sha: str
    registry_fingerprint: str
    adapters: tuple[str, ...]
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "registry_fingerprint": self.registry_fingerprint.lower(),
            "adapters": list(self.adapters),
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
            "candidate_sha": self.candidate_sha,
            "registry_fingerprint": self.registry_fingerprint,
            "adapters": list(self.adapters),
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def verify_official_adapter_evidence(
    *,
    registry_file: Path,
    repository: str,
    candidate_sha: str,
    checked_at: datetime,
) -> IndependentAdapterEvidenceReceipt:
    try:
        registry = load_registry(registry_file)
        assert_activation_ready(
            registry,
            repository=repository,
            candidate_sha=candidate_sha,
            checked_at=checked_at,
        )
    except (
        OfficialAdapterEvidenceError,
        ValueError,
    ) as exc:
        raise IndependentAdapterEvidenceVerificationError(
            "official adapter evidence verification failed"
        ) from exc

    if registry.registry_version != 1:
        raise IndependentAdapterEvidenceVerificationError(
            "unsupported official adapter registry version"
        )
    if registry.repository != repository:
        raise IndependentAdapterEvidenceVerificationError(
            "registry repository mismatch"
        )
    if registry.candidate_sha.lower() != candidate_sha.lower():
        raise IndependentAdapterEvidenceVerificationError(
            "registry candidate SHA mismatch"
        )
    if tuple(item.adapter for item in registry.items) != REQUIRED_ADAPTERS:
        raise IndependentAdapterEvidenceVerificationError(
            "registry adapter set is not canonical"
        )

    return IndependentAdapterEvidenceReceipt(
        verifier_version=1,
        repository=repository,
        candidate_sha=candidate_sha,
        registry_fingerprint=registry.fingerprint,
        adapters=REQUIRED_ADAPTERS,
        verified_at=checked_at.astimezone(timezone.utc),
    )


def write_receipt(
    receipt: IndependentAdapterEvidenceReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise IndependentAdapterEvidenceVerificationError(
            "adapter evidence verification receipt is write-once"
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
