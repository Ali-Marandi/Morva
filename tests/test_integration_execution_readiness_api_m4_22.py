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
    assert "/api/v1/integration-execution/readiness/convergence" in paths
    assert "/api/v1/integration-execution/readiness/convergence/receipts" in paths
    assert "/api/v1/integration-execution/readiness/convergence/history" in paths
    assert "/api/v1/integration-execution/readiness/convergence/freshness" in paths
    assert (
        "/api/v1/integration-execution/readiness/convergence/freshness/policy-bound"
        in paths
    )
    policy_operation = paths[
        "/api/v1/integration-execution/readiness/convergence/freshness/policy-bound"
    ]["get"]
    assert (
        "/api/v1/integration-execution/readiness/convergence/freshness/policies"
        in paths
    )
    assert (
        "/api/v1/integration-execution/readiness/convergence/freshness/policies/{policy_id}"
        in paths
    )
    policy_create_params = {
        parameter["name"]
        for parameter in paths[
            "/api/v1/integration-execution/readiness/convergence/freshness/policies"
        ]["post"]["parameters"]
    }
    assert policy_create_params == set()
    policy_create_schema = paths[
        "/api/v1/integration-execution/readiness/convergence/freshness/policies"
    ]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert policy_create_schema["$ref"] == (
        "#/components/schemas/FreshnessPolicyCreate"
    )
    registry_bound_operation = paths[
        "/api/v1/integration-execution/readiness/convergence/freshness/policy-registry-bound"
    ]["get"]
    registry_bound_params = {
        parameter["name"] for parameter in registry_bound_operation["parameters"]
    }
    assert {
        "candidate_sha",
        "target_environment",
        "organization_scope",
        "organization_scope_id",
        "policy_id",
    } <= registry_bound_params
    policy_params = {
        parameter["name"] for parameter in policy_operation["parameters"]
    }
    assert {
        "candidate_sha",
        "target_environment",
        "organization_scope",
        "organization_scope_id",
        "policy_id",
        "max_age_seconds",
    } <= policy_params
    freshness_operation = paths[
        "/api/v1/integration-execution/readiness/convergence/freshness"
    ]["get"]
    freshness_params = {
        parameter["name"] for parameter in freshness_operation["parameters"]
    }
    assert {
        "candidate_sha",
        "target_environment",
        "organization_scope",
        "organization_scope_id",
        "max_age_seconds",
    } <= freshness_params
    freshness_schema = freshness_operation["responses"][
        "200"
    ]["content"]["application/json"]["schema"]
    assert freshness_schema["$ref"] == (
        "#/components/schemas/ReadinessConvergenceFreshnessResponse"
    )
    receipt_operation = paths[
        "/api/v1/integration-execution/readiness/convergence/receipts"
    ]["post"]
    history_convergence_operation = paths[
        "/api/v1/integration-execution/readiness/convergence/history"
    ]["get"]
    receipt_params = {
        parameter["name"] for parameter in receipt_operation["parameters"]
    }
    history_convergence_params = {
        parameter["name"] for parameter in history_convergence_operation["parameters"]
    }
    assert {
        "candidate_sha",
        "target_environment",
        "organization_scope",
        "organization_scope_id",
    } <= receipt_params
    assert {
        "candidate_sha",
        "target_environment",
        "organization_scope",
        "organization_scope_id",
        "checked_before",
        "before_id",
        "limit",
    } <= history_convergence_params
    convergence_operation = paths["/api/v1/integration-execution/readiness/convergence"]["get"]
    convergence_schema = convergence_operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert convergence_schema["$ref"] == "#/components/schemas/ScopeBoundReadinessConvergenceResponse"
    convergence_params = {parameter["name"] for parameter in convergence_operation["parameters"]}
    assert {
        "candidate_sha",
        "target_environment",
        "organization_scope",
        "organization_scope_id",
    } <= convergence_params
    query_params = {parameter["name"] for parameter in history_operation["parameters"]}
    assert {
        "candidate_sha",
        "target_environment",
        "organization_scope",
        "organization_scope_id",
        "verified_before",
        "before_id",
        "limit",
    } <= query_params
    assert history_schema["$ref"] == "#/components/schemas/IntegrationExecutionReadinessVerificationHistoryResponse"
