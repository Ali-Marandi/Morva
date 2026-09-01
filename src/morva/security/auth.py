from __future__ import annotations

from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient

from morva.runtime.config import settings
from morva.security.policy import Principal, Scope


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url)


def _claim_str(payload: dict[str, Any], *names: str) -> str | None:
    for name in names:
        value = payload.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _required_principal(payload: dict[str, Any]) -> Principal:
    user_id = _claim_str(payload, "sub", "user_id")
    role = _claim_str(payload, "role", "morva_role")
    scope_raw = _claim_str(payload, "scope", "morva_scope")
    scope_id = _claim_str(payload, "scope_id", "org_unit_id", "morva_scope_id")
    if not all((user_id, role, scope_raw, scope_id)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="authenticated principal is incomplete")
    try:
        scope = Scope(scope_raw)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid organization scope") from exc
    return Principal(
        user_id=user_id,
        role=role,
        scope=scope,
        scope_id=scope_id,
        mfa_verified=bool(payload.get("mfa_verified", False)),
    )


def _decode_bearer(token: str) -> dict[str, Any]:
    if not settings.oidc_jwks_url or not settings.oidc_issuer or not settings.oidc_audience:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="authentication provider is not configured")
    try:
        signing_key = _jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "RS384", "RS512"],
            issuer=settings.oidc_issuer,
            audience=settings.oidc_audience,
            options={"require": ["exp", "iat", "sub"]},
        )
        if not isinstance(payload, dict):
            raise ValueError("JWT payload must be an object")
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid bearer token") from exc


def get_current_principal(request: Request) -> Principal:
    """Resolve a trusted identity; production never accepts caller-supplied identity headers."""
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        if settings.production:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bearer authentication required")
        return Principal("local-dev", "admin", Scope.MINISTRY, "local", True)
    return _required_principal(_decode_bearer(authorization[7:].strip()))
