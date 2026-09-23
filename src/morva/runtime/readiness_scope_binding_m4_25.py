from __future__ import annotations

from hashlib import sha256


SUPPORTED_READINESS_SCOPES = frozenset(
    {"school", "district", "province", "ministry"}
)


class ReadinessScopeBindingError(ValueError):
    """Raised when a readiness receipt cannot be bound to an organization scope."""


def normalize_readiness_scope(
    organization_scope: str,
    organization_scope_id: str,
) -> tuple[str, str]:
    scope = organization_scope.strip().lower()
    scope_id = organization_scope_id.strip()
    if scope not in SUPPORTED_READINESS_SCOPES:
        raise ReadinessScopeBindingError(
            "organization_scope must be school, district, province or ministry"
        )
    if not scope_id:
        raise ReadinessScopeBindingError(
            "organization_scope_id is required"
        )
    if len(scope_id) > 100:
        raise ReadinessScopeBindingError(
            "organization_scope_id must not exceed 100 characters"
        )
    return scope, scope_id


def readiness_scope_binding_fingerprint(
    *,
    verification_fingerprint: str,
    organization_scope: str,
    organization_scope_id: str,
) -> str:
    scope, scope_id = normalize_readiness_scope(
        organization_scope,
        organization_scope_id,
    )
    fingerprint = verification_fingerprint.strip().lower()
    if len(fingerprint) != 64 or any(
        char not in "0123456789abcdef" for char in fingerprint
    ):
        raise ReadinessScopeBindingError(
            "verification_fingerprint must be SHA-256"
        )
    canonical = (
        "readiness-scope-binding:v1:"
        f"{fingerprint}:{scope}:{scope_id}"
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def verify_readiness_scope_binding(
    *,
    verification_fingerprint: str,
    organization_scope: str,
    organization_scope_id: str,
    scope_binding_fingerprint: str,
) -> None:
    expected = readiness_scope_binding_fingerprint(
        verification_fingerprint=verification_fingerprint,
        organization_scope=organization_scope,
        organization_scope_id=organization_scope_id,
    )
    actual = scope_binding_fingerprint.strip().lower()
    if actual != expected:
        raise ReadinessScopeBindingError(
            "readiness scope binding fingerprint mismatch"
        )
