from __future__ import annotations


def test_m4_22_readiness_route_is_registered():
    from morva.api.app import app

    assert "/api/v1/integration-execution/readiness" in app.openapi()["paths"]
    operation = app.openapi()["paths"]["/api/v1/integration-execution/readiness"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]
