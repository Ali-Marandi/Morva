# M4.30 Freshness Policy Registry

M4.30 persists the versioned freshness-policy identities introduced by M4.29.

## Contract

Each policy record stores:

- policy version and policy ID;
- maximum convergence age in seconds;
- the deterministic policy SHA-256 fingerprint;
- the actor that recorded the policy and its creation timestamp.

The policy ID/version pair and the fingerprint are unique. Re-recording the same fingerprint is idempotent only for the same actor. A policy ID/version cannot be rebound to a different fingerprint.

## Registry-bound evaluation

`GET /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-bound` resolves the policy from the persisted registry and then evaluates the latest persisted scope-bound convergence observation. The caller no longer supplies the age window to that endpoint.

Policy creation is restricted to a ministry-scoped, MFA-protected principal with the existing evidence-binding permission. Policy creation appends an audit event.

## Safety boundary

M4.30 is still verification and governance only. It performs no provider execution, uses no external credentials, calculates no payroll, mutates payment state and grants no production authority.
