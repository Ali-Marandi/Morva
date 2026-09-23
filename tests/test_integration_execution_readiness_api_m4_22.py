from __future__ import annotations


def test_m4_22_readiness_route_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    assert "/api/v1/integration-execution/readiness" in paths
    assert "/api/v1/integration-execution/readiness/history" in paths

    operation = paths["/api/v1/integration-execution/readiness"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]

    history_operation = paths["/api/v1/integration-execution/readiness/history"]["get"]
    history_schema = history_operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert history_schema["$ref"] == "#/components/schemas/IntegrationExecutionReadinessVerificationHistoryResponse"
    query_params = {parameter["name"] for parameter in history_operation["parameters"]}
    assert {"candidate_sha", "target_environment", "verified_before", "before_id", "limit"} <= query_params
