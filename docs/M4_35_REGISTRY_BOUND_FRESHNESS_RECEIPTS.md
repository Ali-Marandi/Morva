# M4.35 Registry-Bound Freshness Evaluation Receipts

M4.35 persists the M4.34 registry-integrity-bound freshness evaluation as an append-only governance receipt.

## Contract

A receipt records the exact repository/candidate/environment/scope context, policy identity and fingerprint, convergence fingerprint, freshness assessment identity, registry integrity version/count/fingerprint and the final registry-bound fingerprint.

Receipt writes are idempotent on the final binding fingerprint. Replaying the same binding by the same actor returns the existing record; a different actor is rejected.

Persisted receipts are reconstructed through the same runtime contracts used to create them. Structural or fingerprint tampering therefore fails closed.

## API

Create an authenticated receipt:

`POST /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-bound-integrity/receipts`

Read scoped cursor-paginated receipt history:

`GET /api/v1/integration-execution/readiness/convergence/freshness/policy-registry-bound-integrity/receipts`

Receipt creation is ministry-managed and requires the existing privileged evidence-binding permission plus MFA/SoD authorization. History remains read-only and respects the caller's organization scope.

## Persistence

Migration `0029_registry_bound_freshness_receipts` adds the append-only receipt table and indexes for candidate, scope/time, registry fingerprint, state, binding fingerprint and recording actor.

## Safety boundary

This tranche stores and verifies readiness/governance metadata only. It does not execute providers, use external credentials, calculate payroll, mutate payment state or grant production authority.
