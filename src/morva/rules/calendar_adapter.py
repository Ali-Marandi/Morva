from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from .regression_cases import RegressionCase


_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_APPROVED_STATUSES = {"approved", "published"}


class CalendarAdapterContractError(ValueError):
    """A source-calendar resolution is missing valid provenance or verification."""


@dataclass(frozen=True, slots=True)
class CalendarDateResolution:
    """A calendar conversion result plus the authority evidence that must verify it."""

    source_calendar: str
    target_calendar: str
    source_value: str
    effective_on: date
    adapter_id: str
    adapter_version: str
    authority_reference: str
    evidence_sha256: str
    approval_status: str
    reviewed_by: str
    reviewed_at: datetime
    approved_by: str
    approved_at: datetime


class JalaliCalendarAdapter(Protocol):
    """Injected adapter contract; this package intentionally ships no converter."""

    def resolve_jalali_date(self, source_value: str) -> CalendarDateResolution:
        """Resolve one unchanged Jalali source value, retaining its source evidence."""
        ...


class CalendarEvidenceVerifier(Protocol):
    """Trusted verifier for the referenced, independently governed calendar evidence."""

    def verify(self, resolution: CalendarDateResolution) -> bool:
        """Return True only when the evidence hash and approval are independently verified."""
        ...


def _require_text(value: object, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CalendarAdapterContractError(f"calendar resolution {field} is required")


def _validate_resolution(
    *,
    source_value: str,
    resolution: CalendarDateResolution,
) -> None:
    if resolution.source_calendar != "jalali":
        raise CalendarAdapterContractError("calendar source must be jalali")
    if resolution.target_calendar != "gregorian":
        raise CalendarAdapterContractError("calendar target must be gregorian")
    if resolution.source_value != source_value:
        raise CalendarAdapterContractError(
            "calendar adapter must preserve the original source date exactly"
        )
    if type(resolution.effective_on) is not date:
        raise CalendarAdapterContractError(
            "calendar adapter must return a date, not a datetime or string"
        )

    for field in (
        "adapter_id",
        "adapter_version",
        "authority_reference",
        "reviewed_by",
        "approved_by",
    ):
        _require_text(getattr(resolution, field), field)

    digest = resolution.evidence_sha256
    if (
        not isinstance(digest, str)
        or _SHA256.fullmatch(digest) is None
        or digest.lower() == "0" * 64
    ):
        raise CalendarAdapterContractError(
            "calendar resolution evidence_sha256 must be a non-placeholder SHA-256"
        )
    if resolution.approval_status not in _APPROVED_STATUSES:
        raise CalendarAdapterContractError(
            "calendar conversion evidence is not approved/published"
        )
    if resolution.reviewed_by == resolution.approved_by:
        raise CalendarAdapterContractError(
            "calendar evidence reviewer and approver must be distinct"
        )
    if type(resolution.reviewed_at) is not datetime:
        raise CalendarAdapterContractError("calendar evidence reviewed_at is required")
    if type(resolution.approved_at) is not datetime:
        raise CalendarAdapterContractError("calendar evidence approved_at is required")
    if resolution.approved_at < resolution.reviewed_at:
        raise CalendarAdapterContractError(
            "calendar evidence approval cannot precede its review"
        )


def resolve_case_effective_on(
    case: RegressionCase,
    *,
    adapter: JalaliCalendarAdapter,
    evidence_verifier: CalendarEvidenceVerifier,
) -> date:
    """Return a validated effective date for a Golden Case without parsing its source date.

    The original case.effective_date string is passed to the injected adapter verbatim.
    The adapter and evidence verifier must come from a separately governed trust boundary.
    This helper validates the response contract; it does not implement Jalali arithmetic,
    authenticate an official calendar source, or make a synthetic adapter production-safe.
    """
    if not isinstance(case, RegressionCase):
        raise CalendarAdapterContractError("case must be a loaded RegressionCase")
    if not isinstance(case.effective_date, str) or not case.effective_date.strip():
        raise CalendarAdapterContractError("golden case source effective_date is required")

    resolver = getattr(adapter, "resolve_jalali_date", None)
    if not callable(resolver):
        raise CalendarAdapterContractError("an explicit Jalali calendar adapter is required")
    verifier = getattr(evidence_verifier, "verify", None)
    if not callable(verifier):
        raise CalendarAdapterContractError("an independent calendar evidence verifier is required")

    try:
        resolution = resolver(case.effective_date)
    except Exception as exc:
        raise CalendarAdapterContractError("Jalali calendar adapter failed to resolve the source date") from exc

    if not isinstance(resolution, CalendarDateResolution):
        raise CalendarAdapterContractError(
            "calendar adapter must return CalendarDateResolution"
        )

    _validate_resolution(source_value=case.effective_date, resolution=resolution)

    try:
        verified = verifier(resolution)
    except Exception as exc:
        raise CalendarAdapterContractError(
            "calendar evidence verifier failed"
        ) from exc
    if verified is not True:
        raise CalendarAdapterContractError(
            "calendar conversion evidence was not independently verified"
        )
    return resolution.effective_on
