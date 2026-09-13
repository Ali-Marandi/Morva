from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from urllib.parse import urlparse


@dataclass(frozen=True, slots=True)
class PrimarySourceEvidenceRequest:
    source_id: str
    citation: str
    issuer: str
    source_uri: str
    document_hash: str
    adoption_date: str
    effective_from: str
    effective_to: str | None = None
    retrieved_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PrimarySourceEvidenceResult:
    source_id: str
    accepted: bool
    blockers: tuple[str, ...]


def validate_primary_source_evidence(
    request: PrimarySourceEvidenceRequest,
) -> PrimarySourceEvidenceResult:
    blockers: list[str] = []
    source_id = request.source_id.strip()
    if not source_id:
        blockers.append("source_id is required")
    if not request.citation.strip():
        blockers.append("citation is required")
    if not request.issuer.strip():
        blockers.append("issuer is required")

    parsed = urlparse(request.source_uri.strip())
    if parsed.scheme != "https" or not parsed.netloc:
        blockers.append("source_uri must be an absolute HTTPS URI")
    if not request.document_hash or len(request.document_hash) != 64:
        blockers.append("document_hash must be a 64-character SHA-256 hex digest")
    elif any(char not in "0123456789abcdefABCDEF" for char in request.document_hash):
        blockers.append("document_hash must be hexadecimal")

    for field_name in ("adoption_date", "effective_from"):
        value = getattr(request, field_name).strip()
        if len(value) != 10:
            blockers.append(f"{field_name} must use YYYY-MM-DD")

    if request.effective_to is not None and len(request.effective_to.strip()) != 10:
        blockers.append("effective_to must use YYYY-MM-DD when present")
    if request.retrieved_at is None:
        blockers.append("retrieved_at is required for provenance")

    return PrimarySourceEvidenceResult(
        source_id=source_id,
        accepted=not blockers,
        blockers=tuple(dict.fromkeys(blockers)),
    )


def evidence_content_sha256(content: bytes) -> str:
    """Return the canonical SHA-256 digest recorded beside a source artifact."""
    return sha256(content).hexdigest()
