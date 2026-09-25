from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.scope_bound_readiness_convergence_m4_26 import (
    ScopeBoundReadinessConvergence,
)


class ReadinessConvergenceFreshnessError(ValueError):
    """Raised when a convergence freshness assessment is invalid."""


@dataclass(frozen=True, slots=True)
class ReadinessConvergenceFreshnessAssessment:
    freshness_version: int
    convergence_fingerprint: str
    checked_at: datetime
    observed_at: datetime
    max_age_seconds: int
    age_seconds: int
    state: str
    blockers: tuple[str, ...]
    fingerprint: str

    def __post_init__(self) -> None:
        if self.freshness_version != 1:
            raise ReadinessConvergenceFreshnessError(
                "unsupported convergence freshness version"
            )
        if self.checked_at.tzinfo is None or self.observed_at.tzinfo is None:
            raise ReadinessConvergenceFreshnessError(
                "freshness timestamps must be timezone-aware"
            )
        if self.max_age_seconds < 1:
            raise ReadinessConvergenceFreshnessError(
                "max_age_seconds must be positive"
            )
        if self.age_seconds < 0:
            raise ReadinessConvergenceFreshnessError(
                "age_seconds cannot be negative"
            )
        if self.state not in {"fresh", "stale", "blocked"}:
            raise ReadinessConvergenceFreshnessError(
                "state must be fresh, stale or blocked"
            )
        if self.state == "fresh" and self.blockers:
            raise ReadinessConvergenceFreshnessError(
                "fresh assessment cannot contain blockers"
            )
        if self.state in {"stale", "blocked"} and not self.blockers:
            raise ReadinessConvergenceFreshnessError(
                "non-fresh assessment must contain blockers"
            )
        for name, value in (
            ("convergence_fingerprint", self.convergence_fingerprint),
            ("fingerprint", self.fingerprint),
        ):
            if len(value) != 64 or any(
                char not in "0123456789abcdef" for char in value.lower()
            ):
                raise ReadinessConvergenceFreshnessError(
                    f"{name} must be SHA-256"
                )

        expected = _fingerprint(
            convergence_fingerprint=self.convergence_fingerprint,
            checked_at=self.checked_at,
            observed_at=self.observed_at,
            max_age_seconds=self.max_age_seconds,
            age_seconds=self.age_seconds,
            state=self.state,
            blockers=self.blockers,
        )
        if self.fingerprint.lower() != expected:
            raise ReadinessConvergenceFreshnessError(
                "convergence freshness fingerprint mismatch"
            )

    @property
    def fresh(self) -> bool:
        return self.state == "fresh"

    def to_payload(self) -> dict[str, object]:
        return {
            "freshness_version": self.freshness_version,
            "convergence_fingerprint": self.convergence_fingerprint,
            "checked_at": self.checked_at.astimezone(timezone.utc).isoformat(),
            "observed_at": self.observed_at.astimezone(timezone.utc).isoformat(),
            "max_age_seconds": self.max_age_seconds,
            "age_seconds": self.age_seconds,
            "state": self.state,
            "blockers": list(self.blockers),
            "fresh": self.fresh,
            "fingerprint": self.fingerprint,
        }


def assess_readiness_convergence_freshness(
    convergence: ScopeBoundReadinessConvergence,
    *,
    observed_at: datetime,
    max_age_seconds: int,
) -> ReadinessConvergenceFreshnessAssessment:
    if observed_at.tzinfo is None:
        raise ReadinessConvergenceFreshnessError(
            "observed_at must be timezone-aware"
        )
    if max_age_seconds < 1:
        raise ReadinessConvergenceFreshnessError(
            "max_age_seconds must be positive"
        )

    checked_at = convergence.checked_at.astimezone(timezone.utc)
    now = observed_at.astimezone(timezone.utc)
    age_delta = now - checked_at
    age_seconds = age_delta.days * 86400 + age_delta.seconds
    blockers: list[str] = []

    if age_delta.total_seconds() < 0:
        blockers.append("CONVERGENCE_OBSERVATION_IN_FUTURE")
    if convergence.state != "converged":
        blockers.append("CONVERGENCE_NOT_CONFIRMED")
    if age_seconds > max_age_seconds:
        blockers.append("CONVERGENCE_STALE")

    if blockers:
        state = "blocked" if "CONVERGENCE_NOT_CONFIRMED" in blockers else "stale"
    else:
        state = "fresh"

    fingerprint = _fingerprint(
        convergence_fingerprint=convergence.fingerprint,
        checked_at=checked_at,
        observed_at=now,
        max_age_seconds=max_age_seconds,
        age_seconds=max(age_seconds, 0),
        state=state,
        blockers=tuple(blockers),
    )
    return ReadinessConvergenceFreshnessAssessment(
        freshness_version=1,
        convergence_fingerprint=convergence.fingerprint.lower(),
        checked_at=checked_at,
        observed_at=now,
        max_age_seconds=max_age_seconds,
        age_seconds=max(age_seconds, 0),
        state=state,
        blockers=tuple(blockers),
        fingerprint=fingerprint,
    )


def _fingerprint(
    *,
    convergence_fingerprint: str,
    checked_at: datetime,
    observed_at: datetime,
    max_age_seconds: int,
    age_seconds: int,
    state: str,
    blockers: tuple[str, ...],
) -> str:
    payload = {
        "freshness_version": 1,
        "convergence_fingerprint": convergence_fingerprint.lower(),
        "checked_at": checked_at.astimezone(timezone.utc).isoformat(),
        "observed_at": observed_at.astimezone(timezone.utc).isoformat(),
        "max_age_seconds": max_age_seconds,
        "age_seconds": age_seconds,
        "state": state,
        "blockers": list(blockers),
    }
    return sha256(
        json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
