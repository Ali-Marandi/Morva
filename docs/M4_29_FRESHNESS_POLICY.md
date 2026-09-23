# M4.29 Freshness Policy Identity

M4.29 adds an explicit, versioned identity for the freshness policy used by M4.28.

## Contract

A freshness policy contains:

- policy version;
- policy ID;
- maximum allowed convergence age in seconds;
- deterministic SHA-256 policy fingerprint.

The policy fingerprint is carried alongside the M4.28 freshness result through the policy-bound contract. A freshness assessment cannot be bound to a policy whose maximum age differs from the assessment that produced it.

## Why this boundary exists

M4.28 deliberately accepts the maximum age explicitly so no hidden operational policy is invented in code. M4.29 adds identity to that explicit policy, so the age rule used by one observer can be audited and compared with another observer's decision.

No default operational or legal freshness window is silently introduced by this milestone.

## API

GET /api/v1/integration-execution/readiness/convergence/freshness/policy-bound

The endpoint requires the exact organization scope, an explicit policy_id and an explicit max_age_seconds. Non-ministry principals remain restricted to their own scope.

## Safety boundary

M4.29 remains evidence and verification only. It performs no provider execution, uses no external credentials, calculates no payroll, mutates payment state and grants no production authority.
