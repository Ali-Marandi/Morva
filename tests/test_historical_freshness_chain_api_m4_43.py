from __future__ import annotations


def test_m4_43_historical_freshness_chain_verify_route_is_registered():
    from morva.api.app import app

    paths = app.openapi()["paths"]
    path = (
        "/api/v1/integration-execution/readiness/convergence/freshness/"
        "policy-registry-snapshot-bound/receipt-lineage/{lineage_id}/verify-chain"
    )
    assert path in paths

    operation = paths[path]["get"]
    parameter_names = {parameter["name"] for parameter in operation["parameters"]}
    assert "lineage_id" in parameter_names

    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"] == (
        "#/components/schemas/HistoricalFreshnessChainVerificationResponse"
    )
