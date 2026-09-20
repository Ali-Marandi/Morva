from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path

from morva.runtime.production_readiness_convergence import (
    ProductionReadinessConvergence,
    ProductionReadinessConvergenceError,
)
from morva.runtime.production_readiness_handoff import (
    ProductionReadinessHandoffError,
    load_handoff,
    verify_handoff_sources,
)


class IndependentHandoffVerificationError(ValueError):
    """Raised when a readiness handoff cannot be independently verified."""


@dataclass(frozen=True, slots=True)
class IndependentHandoffVerificationReceipt:
    verifier_version: int
    repository: str
    release_id: str
    tag: str
    candidate_sha: str
    convergence_fingerprint: str
    handoff_fingerprint: str
    verified_at: datetime

    @property
    def fingerprint(self) -> str:
        payload = {
            "verifier_version": self.verifier_version,
            "repository": self.repository,
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha.lower(),
            "convergence_fingerprint": self.convergence_fingerprint.lower(),
            "handoff_fingerprint": self.handoff_fingerprint.lower(),
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
            "release_id": self.release_id,
            "tag": self.tag,
            "candidate_sha": self.candidate_sha,
            "convergence_fingerprint": self.convergence_fingerprint,
            "handoff_fingerprint": self.handoff_fingerprint,
            "verified_at": self.verified_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def _load_convergence(path: Path) -> ProductionReadinessConvergence:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        convergence = ProductionReadinessConvergence(
            convergence_version=int(payload["convergence_version"]),
            repository=payload["repository"],
            release_id=payload["release_id"],
            tag=payload["tag"],
            candidate_sha=payload["candidate_sha"],
            lineage_fingerprint=payload["lineage_fingerprint"],
            lineage_verification_fingerprint=(
                payload["lineage_verification_fingerprint"]
            ),
            full_policy_fingerprint=payload["full_policy_fingerprint"],
            certification_verification_fingerprint=(
                payload["certification_verification_fingerprint"]
            ),
            verified_roles=tuple(payload["verified_roles"]),
            source_environment=payload["source_environment"],
            target_environment=payload["target_environment"],
            converged_at=datetime.fromisoformat(payload["converged_at"]),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        raise IndependentHandoffVerificationError(
            "M3.72 convergence structure is invalid"
        ) from exc
    if payload.get("fingerprint") != convergence.fingerprint:
        raise IndependentHandoffVerificationError(
            "M3.72 convergence fingerprint mismatch"
        )
    return convergence


def verify_handoff(
    *,
    convergence_file: Path,
    handoff_file: Path,
    source_root: Path,
    repository: str,
    tag: str,
    candidate_sha: str,
) -> IndependentHandoffVerificationReceipt:
    try:
        convergence = _load_convergence(convergence_file)
        handoff = load_handoff(handoff_file)
        verify_handoff_sources(handoff=handoff, root=source_root)
    except (
        IndependentHandoffVerificationError,
        ProductionReadinessConvergenceError,
        ProductionReadinessHandoffError,
        ValueError,
    ) as exc:
        raise IndependentHandoffVerificationError(
            "convergence or handoff verification failed"
        ) from exc

    if (
        convergence.repository != repository
        or convergence.tag != tag
        or convergence.candidate_sha.lower() != candidate_sha.lower()
    ):
        raise IndependentHandoffVerificationError(
            "convergence identity mismatch"
        )
    if (
        handoff.repository != repository
        or handoff.tag != tag
        or handoff.candidate_sha.lower() != candidate_sha.lower()
    ):
        raise IndependentHandoffVerificationError(
            "handoff identity mismatch"
        )
    if handoff.release_id != convergence.release_id:
        raise IndependentHandoffVerificationError(
            "handoff release id mismatch"
        )
    if handoff.convergence_fingerprint.lower() != convergence.fingerprint.lower():
        raise IndependentHandoffVerificationError(
            "handoff convergence fingerprint mismatch"
        )
    convergence_relative = str(convergence_file.relative_to(source_root))
    matching = [
        source for source in handoff.sources
        if source.path == convergence_relative
    ]
    if len(matching) != 1:
        raise IndependentHandoffVerificationError(
            "handoff must contain exactly one convergence source"
        )
    recorded = matching[0]
    data = convergence_file.read_bytes()
    if sha256(data).hexdigest() != recorded.sha256.lower():
        raise IndependentHandoffVerificationError(
            "convergence source hash does not match handoff"
        )
    if len(data) != recorded.size_bytes:
        raise IndependentHandoffVerificationError(
            "convergence source size does not match handoff"
        )

    return IndependentHandoffVerificationReceipt(
        verifier_version=1,
        repository=repository,
        release_id=handoff.release_id,
        tag=tag,
        candidate_sha=candidate_sha,
        convergence_fingerprint=convergence.fingerprint,
        handoff_fingerprint=handoff.fingerprint,
        verified_at=datetime.now(timezone.utc),
    )


def write_receipt(
    receipt: IndependentHandoffVerificationReceipt,
    path: Path,
) -> None:
    if path.exists():
        raise IndependentHandoffVerificationError(
            "independent handoff receipt is write-once"
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
