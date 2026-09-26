from __future__ import annotations

from morva.api.app import app


def _is_protected_route(route) -> bool:
    if not getattr(route, "path", "").startswith("/api/v1/"):
        return True
    dependencies = getattr(getattr(route, "dependant", None), "dependencies", [])
    return any(
        getattr(getattr(dependency, "call", None), "__name__", "") == "get_current_principal"
        for dependency in dependencies
    )


def test_all_v1_api_routes_are_authenticated() -> None:
    unprotected = [
        route.path
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/v1/")
        and not _is_protected_route(route)
    ]
    assert unprotected == []
