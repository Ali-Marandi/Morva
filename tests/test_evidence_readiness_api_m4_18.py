from __future__ import annotations


def test_evidence_readiness_route_is_registered():
    from morva.api.app import app

    assert "/api/v1/evidence-submissions/readiness" in app.openapi()["paths"]
