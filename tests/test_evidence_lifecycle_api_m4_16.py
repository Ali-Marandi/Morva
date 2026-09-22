from __future__ import annotations


def test_evidence_lifecycle_routes_are_registered():
    from morva.api.app import app

    paths = set(app.openapi()["paths"])
    assert "/api/v1/evidence-submissions/{evidence_id}/supersede" in paths
    assert "/api/v1/evidence-submissions/lifecycle" in paths
