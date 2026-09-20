from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.final_production_readiness import (
    FinalProductionReadinessError,
    FinalProductionReadinessGate,
    _load_freshness_gate,
    _load_technical_gate,
)


class FinalReadinessVerificationError(ValueError):
    """Raised when the final readiness gate fails independent verification."""


@dataclass(frozen=True, slots=True)
class FinalReadinessVerificationReceipt:
    verifier_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    technical_gate_fingerprint: str
    freshness_gate_fingerprint: str
    final_gate_fingerprint: str
    policy_fingerprint: str
    source_environment: str
    target_environment: str
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "technical_gate_fingerprint": (
                self.technical_gate_fingerprint.lower()
            ),
            "freshness_gate_fingerprint": (
                self.freshness_gate_fingerprint.lower()
            ),
            "final_gate_fingerprint": self.final_gate_fingerprint.lower(),
            "policy_fingerprint": self.policy_fingerprint.lower(),
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
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
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "technical_gate_fingerprint": self.technical_gate_fingerprint,
            "freshness_gate_fingerprint": self.freshness_gate_fingerprint,
            "final_gate_fingerprint": self.final_gate_fingerprint,
            "policy_fingerprint": self.policy_fingerprint,
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_final_gate(path: Path) -> FinalProductionReadinessGate:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        gate = FinalProductionReadinessGate(
            gate_version=int(payload["gate_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            bundle_fingerprint=payload["bundle_fingerprint"],
            technical_readiness_fingerprint=(
                payload["technical_readiness_fingerprint"]
            ),
            freshness_gate_fingerprint=payload["freshness_gate_fingerprint"],
            policy_fingerprint=payload["policy_fingerprint"],
            source_environment=payload["source_environment"],
            target_environment=payload["target_environment"],
            checked_at=datetime.fromisoformat(payload["checked_at"]),
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise FinalReadinessVerificationError(
            "final readiness gate structure is invalid"
        ) from exc
    if payload.get("fingerprint") != gate.fingerprint:
        raise FinalReadinessVerificationError(
            "final readiness gate fingerprint mismatch"
        )
    return gate


def verify_final_readiness(
    *,
    technical_gate: Path,
    freshness_gate: Path,
    final_gate: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> FinalReadinessVerificationReceipt:
    try:
        technical = _load_technical_gate(technical_gate)
        freshness = _load_freshness_gate(freshness_gate)
        final = _load_final_gate(final_gate)
    except (
        FinalProductionReadinessError,
        FinalReadinessVerificationError,
        ValueError,
    ) as exc:
        raise FinalReadinessVerificationError(str(exc)) from exc

    if not technical.policy_passed:
        raise FinalReadinessVerificationError(
            "technical policy gate did not pass"
        )
    if final.repository != repository or final.tag != tag:
        raise FinalReadinessVerificationError(
            "final readiness repository/tag mismatch"
        )
    if final.candidate_sha.lower() != candidate_sha.lower():
        raise FinalReadinessVerificationError(
            "final readiness candidate SHA mismatch"
        )
    if final.release_id != technical.release_id:
        raise FinalReadinessVerificationError(
            "final readiness release id mismatch"
        )
    if final.bundle_fingerprint.lower() != technical.bundle_fingerprint.lower():
        raise FinalReadinessVerificationError(
            "final readiness bundle fingerprint mismatch"
        )
    if (
        final.technical_readiness_fingerprint.lower()
        != technical.fingerprint.lower()
    ):
        raise FinalReadinessVerificationError(
            "technical readiness fingerprint mismatch"
        )
    if (
        final.freshness_gate_fingerprint.lower()
        != freshness.fingerprint.lower()
    ):
        raise FinalReadinessVerificationError(
            "freshness fingerprint mismatch"
        )
    if final.policy_fingerprint.lower() != technical.policy_fingerprint.lower():
        raise FinalReadinessVerificationError(
            "policy fingerprint mismatch"
        )
    if final.source_environment != technical.source_environment:
        raise FinalReadinessVerificationError(
            "source environment mismatch"
        )
    if final.target_environment != "production":
        raise FinalReadinessVerificationError(
            "target environment is not production"
        )
    if final.checked_at < technical.checked_at or final.checked_at < freshness.checked_at:
        raise FinalReadinessVerificationError(
            "final check time precedes preceding readiness check"
        )

    return FinalReadinessVerificationReceipt(
        verifier_version=1,
        repository=repository,
        release_id=final.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        technical_gate_fingerprint=technical.fingerprint,
        freshness_gate_fingerprint=freshness.fingerprint,
        final_gate_fingerprint=final.fingerprint,
        policy_fingerprint=technical.policy_fingerprint,
        source_environment=final.source_environment,
        target_environment=final.target_environment,
        verified_at=datetime.now(timezone.utc),
    )


def write_receipt(
    receipt: FinalReadinessVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise FinalReadinessVerificationError(
            "final readiness verification receipt is write-once"
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
