# M4.28 Readiness Convergence Freshness

M4.28 adds an explicit freshness check over persisted M4.27 scope-bound convergence observations.

## Contract

A persisted convergence observation is considered fresh only when:

- the observation timestamp is not in the future;
- the persisted convergence state is converged;
- its age does not exceed an explicitly supplied maximum age in seconds.

No default freshness policy is embedded in the contract. The caller must supply the allowed age window so policy ownership remains explicit.

## States

- fresh: the convergence observation is confirmed and within the supplied age window.
- stale: the observation is older than the supplied window, or its timestamp is ahead of the observation clock.
- blocked: the persisted convergence itself was not confirmed.

The result contains deterministic blocker codes such as CONVERGENCE_STALE, CONVERGENCE_OBSERVATION_IN_FUTURE and CONVERGENCE_NOT_CONFIRMED, plus its own SHA-256 fingerprint.

## API

GET /api/v1/integration-execution/readiness/convergence/freshness

The endpoint requires an exact organization scope. Non-ministry principals remain restricted to their own scope. The freshness window is supplied through max_age_seconds.

## Safety boundary

M4.28 is read-only verification. It does not execute providers, access external credentials, calculate payroll, mutate payment state or authorize production execution.
