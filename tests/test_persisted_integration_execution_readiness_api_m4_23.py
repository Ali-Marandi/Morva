from __future__ import annotations


def test_m4_23_verify_route_is_registered():
    from morva.api.app import app

    path = "/api/v1/integration-execution/readiness/verify"
    operation = app.openapi()["paths"][path]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert operation["responses"]["409"]["description"]


def test_m4_23_verify_route_does_not_expose_write_methods():
    from morva.api.app import app

    path = "/api/v1/integration-execution/readiness/verify"
    methods = set(app.openapi()["paths"][path])
    assert methods == {"get"}
