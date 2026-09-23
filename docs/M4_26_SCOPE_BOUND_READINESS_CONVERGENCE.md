# M4.26 Scope-Bound Readiness Convergence

M4.26 checks whether a persisted, independently verified integration-readiness receipt still agrees with the current authoritative evidence state for the exact organization scope to which the receipt is bound.

## Rebuild chain

For a selected receipt:

`persisted M4.21 receipt`
→ `exact scope filter`
→ `current accepted evidence registry`
→ `current role-binding convergence`
→ `current lifecycle assessment`
→ `current evidence-readiness assessment`
→ `scope-bound convergence result`

The current evidence readiness is rebuilt from persisted evidence records. It is not copied from the persisted readiness receipt and is not trusted merely because the old fingerprint is present.

## Convergence states

A result is `converged` only when:

- the persisted assessment was itself `ready`;
- current scoped evidence readiness is complete;
- the persisted evidence-readiness fingerprint exactly matches the current scoped evidence-readiness fingerprint.

Otherwise the result is `blocked` with deterministic blocker codes, including:

- `PERSISTED_READINESS_NOT_READY`
- `CURRENT_EVIDENCE_READINESS_INCOMPLETE`
- `EVIDENCE_READINESS_FINGERPRINT_MISMATCH`

The resulting convergence object has its own SHA-256 fingerprint and includes the exact candidate, target environment, organization scope and checked timestamp.

## API

`GET /api/v1/integration-execution/readiness/convergence`

A non-ministry principal is forced to its own scope. A ministry principal must select an exact scope for convergence because convergence is deliberately an exact-scope operation rather than a cross-scope aggregate.

## Safety boundary

M4.26 is verification-only. It performs no provider calls, uses no external credentials, calculates no payroll, mutates no payment state and does not authorize production execution.
