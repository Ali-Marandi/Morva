from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urlparse


class AuthoritativeEvidenceIntakeError(ValueError):
    """Raised when authoritative evidence cannot enter the trusted registry."""


ALLOWED_STATUS = ("pending", "accepted", "rejected")
ALLOWED_SOURCE_TYPES = (
    "legal_rule",
    "master_data",
    "payroll_sample",
    "personnel_order",
    "adapter_contract",
    "security_assessment",
    "dr_report",
    "reconciliation",
    "finance_approval",
    "operations_approval",
    "load_validation",
    "release_certification",
    "publication",
    "deployment_validation",
)


def _parse_timestamp(name: str, value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise AuthoritativeEvidenceIntakeError(
            f"{name} must be ISO-8601"
        ) from exc
    if parsed.tzinfo is None:
        raise AuthoritativeEvidenceIntakeError(
            f"{name} must include a timezone"
        )
    return parsed


def _validate_sha256(name: str, value: str) -> None:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower()):
        raise AuthoritativeEvidenceIntakeError(
            f"{name} must be a SHA-256 digest"
        )


def _validate_source_uri(value: str) -> None:
    parsed = urlparse(value)
    if not parsed.scheme:
        raise AuthoritativeEvidenceIntakeError(
            "source_uri must include a URI scheme"
        )
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise AuthoritativeEvidenceIntakeError(
            "source_uri has an invalid HTTP(S) authority"
        )


@dataclass(frozen=True, slots=True)
class AuthoritativeEvidenceItem:
    intake_version: int
    evidence_id: str
    source_type: str
    source_uri: str
    source_sha256: str
    issuer: str
    population_scope: str
    effective_from: str
    effective_to: str | None
    status: str
    approved_by: str | None = None
    approved_at: str | None = None
    expires_at: str | None = None

    def __post_init__(self) -> None:
        if self.intake_version != 1:
            raise AuthoritativeEvidenceIntakeError(
                "unsupported authoritative evidence intake version"
            )
        for name, value in (
            ("evidence_id", self.evidence_id),
            ("issuer", self.issuer),
            ("population_scope", self.population_scope),
            ("source_uri", self.source_uri),
        ):
            if not value.strip():
                raise AuthoritativeEvidenceIntakeError(f"{name} is required")
        if self.source_type not in ALLOWED_SOURCE_TYPES:
            raise AuthoritativeEvidenceIntakeError("unsupported source_type")
        if self.status not in ALLOWED_STATUS:
            raise AuthoritativeEvidenceIntakeError("unsupported evidence status")
        _validate_source_uri(self.source_uri)
        _validate_sha256("source_sha256", self.source_sha256)

        effective_from = _parse_timestamp("effective_from", self.effective_from)
        if self.effective_to is not None:
            effective_to = _parse_timestamp("effective_to", self.effective_to)
            if effective_to <= effective_from:
                raise AuthoritativeEvidenceIntakeError(
                    "effective_to must be later than effective_from"
                )

        if self.status == "accepted":
            if not self.approved_by or not self.approved_by.strip():
                raise AuthoritativeEvidenceIntakeError(
                    "accepted evidence requires approved_by"
                )
            if self.approved_at is None:
                raise AuthoritativeEvidenceIntakeError(
                    "accepted evidence requires approved_at"
                )
        if self.approved_at is not None:
            _parse_timestamp("approved_at", self.approved_at)
        if self.expires_at is not None:
            _parse_timestamp("expires_at", self.expires_at)

    @property
    def fingerprint(self) -> str:
        payload = self.to_payload(include_fingerprint=False)
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def to_payload(self, *, include_fingerprint: bool = True) -> dict[str, object]:
        payload: dict[str, object] = {
            "intake_version": self.intake_version,
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "source_uri": self.source_uri,
            "source_sha256": self.source_sha256.lower(),
            "issuer": self.issuer,
            "population_scope": self.population_scope,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "expires_at": self.expires_at,
        }
        if include_fingerprint:
            payload["fingerprint"] = self.fingerprint
        return payload


@dataclass(frozen=True, slots=True)
class AuthoritativeEvidenceRegistry:
    registry_version: int
    items: tuple[AuthoritativeEvidenceItem, ...]
    registered_at: datetime

    def __post_init__(self) -> None:
        if self.registry_version != 1:
            raise AuthoritativeEvidenceIntakeError(
                "unsupported evidence registry version"
            )
        if not self.items:
            raise AuthoritativeEvidenceIntakeError(
                "authoritative evidence registry cannot be empty"
            )
        ids = [item.evidence_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise AuthoritativeEvidenceIntakeError(
                "duplicate authoritative evidence_id"
            )
        if self.registered_at.tzinfo is None:
            raise AuthoritativeEvidenceIntakeError(
                "registered_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "registry_version": self.registry_version,
            "items": [item.to_payload() for item in self.items],
        }
        canonical = json.dumps(
            payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def is_activation_ready(self, checked_at: datetime) -> bool:
        if checked_at.tzinfo is None:
            raise AuthoritativeEvidenceIntakeError(
                "checked_at must be timezone-aware"
            )
        now = checked_at.astimezone(timezone.utc)
        for item in self.items:
            if item.status != "accepted":
                return False
            effective_from = _parse_timestamp(
                "effective_from", item.effective_from
            )
            if effective_from > now:
                return False
            if item.effective_to is not None:
                effective_to = _parse_timestamp("effective_to", item.effective_to)
                if effective_to <= now:
                    return False
            if item.approved_at is None:
                return False
            approved_at = _parse_timestamp("approved_at", item.approved_at)
            if approved_at > now:
                return False
            if item.expires_at is not None:
                expires_at = _parse_timestamp("expires_at", item.expires_at)
                if expires_at <= now:
                    return False
        return True

    def to_payload(self) -> dict[str, object]:
        return {
            "registry_version": self.registry_version,
            "items": [item.to_payload() for item in self.items],
            "registered_at": self.registered_at.isoformat(),
            "fingerprint": self.fingerprint,
        }


def build_registry(
    items: tuple[AuthoritativeEvidenceItem, ...],
    *,
    registered_at: datetime,
) -> AuthoritativeEvidenceRegistry:
    return AuthoritativeEvidenceRegistry(
        registry_version=1,
        items=tuple(sorted(items, key=lambda item: item.evidence_id)),
        registered_at=registered_at,
    )


def write_registry(
    registry: AuthoritativeEvidenceRegistry,
    path: Path,
) -> None:
    if path.exists():
        raise AuthoritativeEvidenceIntakeError(
            "authoritative evidence registry is write-once"
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
