from __future__ import annotations


def test_m4_23_independent_readiness_verify_route_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    path = "/api/v1/integration-execution/readiness/verify"

    assert path in paths
    operation = paths[path]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]
