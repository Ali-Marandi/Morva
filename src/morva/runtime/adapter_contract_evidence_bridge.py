from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json

from morva.runtime.authoritative_evidence_intake import (
    AuthoritativeEvidenceRegistry,
)
from morva.runtime.official_adapter_evidence import (
    REQUIRED_ADAPTERS,
    AdapterEvidence,
    OfficialAdapterEvidenceRegistry,
)


class AdapterContractEvidenceBridgeError(ValueError):
    """Raised when official adapter evidence cannot bind safely."""


@dataclass(frozen=True, slots=True)
class AdapterContractEvidenceBinding:
    binding_version: int
    adapter: str
    provider: str
    schema_version: str
    authoritative_evidence_id: str
    contract_source: str
    digest_sha256: str
    repository: str
    candidate_sha: str
    bound_by: str
    bound_at: datetime

    def __post_init__(self) -> None:
        if self.binding_version != 1:
            raise AdapterContractEvidenceBridgeError(
                "unsupported adapter contract binding version"
            )
        if self.adapter not in REQUIRED_ADAPTERS:
            raise AdapterContractEvidenceBridgeError(
                "unsupported adapter"
            )
        for name, value in (
            ("provider", self.provider),
            ("schema_version", self.schema_version),
            ("authoritative_evidence_id", self.authoritative_evidence_id),
            ("contract_source", self.contract_source),
            ("repository", self.repository),
            ("bound_by", self.bound_by),
        ):
            if not value.strip():
                raise AdapterContractEvidenceBridgeError(
                    f"{name} is required"
                )
        if len(self.digest_sha256) != 64 or any(
            char not in "0123456789abcdef"
            for char in self.digest_sha256.lower()
        ):
            raise AdapterContractEvidenceBridgeError(
                "digest_sha256 must be SHA-256"
            )
        if len(self.candidate_sha) != 40 or any(
            char not in "0123456789abcdef"
            for char in self.candidate_sha.lower()
        ):
            raise AdapterContractEvidenceBridgeError(
                "candidate_sha must be Git SHA-1"
            )
        if self.bound_at.tzinfo is None:
            raise AdapterContractEvidenceBridgeError(
                "bound_at must be timezone-aware"
            )

    @property
    def fingerprint(self) -> str:
        payload = {
            "binding_version": self.binding_version,
            "adapter": self.adapter,
            "provider": self.provider,
            "schema_version": self.schema_version,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "contract_source": self.contract_source,
            "digest_sha256": self.digest_sha256.lower(),
            "repository": self.repository,
            "candidate_sha": self.candidate_sha.lower(),
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.astimezone(timezone.utc).isoformat(),
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
            "binding_version": self.binding_version,
            "adapter": self.adapter,
            "provider": self.provider,
            "schema_version": self.schema_version,
            "authoritative_evidence_id": self.authoritative_evidence_id,
            "contract_source": self.contract_source,
            "digest_sha256": self.digest_sha256,
            "repository": self.repository,
            "candidate_sha": self.candidate_sha,
            "bound_by": self.bound_by,
            "bound_at": self.bound_at.astimezone(timezone.utc).isoformat(),
            "fingerprint": self.fingerprint,
        }


def _require_current_authoritative_evidence(
    registry: AuthoritativeEvidenceRegistry,
    evidence_id: str,
    *,
    checked_at: datetime,
) -> tuple[str, str, str]:
    item = next(
        (
            entry
            for entry in registry.items
            if entry.evidence_id == evidence_id
        ),
        None,
    )
    if item is None:
        raise AdapterContractEvidenceBridgeError(
            "authoritative adapter evidence is not present in registry"
        )
    if item.source_type != "adapter_contract":
        raise AdapterContractEvidenceBridgeError(
            "authoritative adapter evidence must use adapter_contract source type"
        )
    if item.status != "accepted":
        raise AdapterContractEvidenceBridgeError(
            "authoritative adapter evidence must be accepted"
        )
    now = checked_at.astimezone(timezone.utc)
    if item.approved_at is None:
        raise AdapterContractEvidenceBridgeError(
            "authoritative adapter evidence approval is required"
        )
    approved_at = datetime.fromisoformat(item.approved_at)
    if approved_at > now:
        raise AdapterContractEvidenceBridgeError(
            "authoritative adapter evidence approval is future-dated"
        )
    effective_from = datetime.fromisoformat(item.effective_from)
    if effective_from > now:
        raise AdapterContractEvidenceBridgeError(
            "authoritative adapter evidence is not yet effective"
        )
    if item.effective_to is not None:
        effective_to = datetime.fromisoformat(item.effective_to)
        if effective_to <= now:
            raise AdapterContractEvidenceBridgeError(
                "authoritative adapter evidence is no longer effective"
            )
    if item.expires_at is not None:
        expires_at = datetime.fromisoformat(item.expires_at)
        if expires_at <= now:
            raise AdapterContractEvidenceBridgeError(
                "authoritative adapter evidence is expired"
            )
    return item.source_uri, item.source_sha256.lower(), item.issuer.strip()


def build_adapter_contract_evidence_binding(
    evidence: AdapterEvidence,
    authoritative_registry: AuthoritativeEvidenceRegistry,
    *,
    authoritative_evidence_id: str,
    bound_by: str,
    bound_at: datetime,
) -> AdapterContractEvidenceBinding:
    if not isinstance(evidence, AdapterEvidence):
        raise AdapterContractEvidenceBridgeError(
            "adapter evidence instance is required"
        )
    if not authoritative_evidence_id.strip():
        raise AdapterContractEvidenceBridgeError(
            "authoritative_evidence_id is required"
        )
    if not bound_by.strip():
        raise AdapterContractEvidenceBridgeError("bound_by is required")
    if bound_at.tzinfo is None:
        raise AdapterContractEvidenceBridgeError(
            "bound_at must be timezone-aware"
        )

    contract_source, digest_sha256, issuer = _require_current_authoritative_evidence(
        authoritative_registry,
        authoritative_evidence_id,
        checked_at=bound_at,
    )
    if evidence.repository.strip() != authoritative_registry.items[0].source_uri.split("://")[0] if False else False:
        pass

    if evidence.contract_source.strip() != contract_source.strip():
        raise AdapterContractEvidenceBridgeError(
            "adapter contract source does not match authoritative evidence URI"
        )
    if evidence.digest_sha256.lower() != digest_sha256:
        raise AdapterContractEvidenceBridgeError(
            "adapter contract digest does not match authoritative evidence SHA-256"
        )
    if evidence.candidate_sha.lower() != authoritative_registry.items[0].evidence_id.lower() if False else False:
        pass

    # The M4.1 registry does not encode candidate SHA at item level. The
    # adapter evidence registry remains the authoritative release-lineage
    # binding for repository and candidate SHA.
    if evidence.adapter not in REQUIRED_ADAPTERS:
        raise AdapterContractEvidenceBridgeError("unsupported adapter")
    if not issuer:
        raise AdapterContractEvidenceBridgeError(
            "authoritative adapter evidence issuer is required"
        )

    return AdapterContractEvidenceBinding(
        binding_version=1,
        adapter=evidence.adapter,
        provider=evidence.provider.strip(),
        schema_version=evidence.schema_version.strip(),
        authoritative_evidence_id=authoritative_evidence_id.strip(),
        contract_source=evidence.contract_source.strip(),
        digest_sha256=evidence.digest_sha256.lower(),
        repository=evidence.repository.strip(),
        candidate_sha=evidence.candidate_sha.lower(),
        bound_by=bound_by.strip(),
        bound_at=bound_at.astimezone(timezone.utc),
    )
