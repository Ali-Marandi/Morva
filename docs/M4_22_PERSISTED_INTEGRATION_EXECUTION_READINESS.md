# M4.22 Persisted Integration-Execution Readiness

M4.22 persists the M4.21 independent-verification result as an append-only receipt and exposes the latest receipt through a read-only API.

## Persistence model

Each receipt preserves:

- the exact repository and candidate commit SHA;
- target environment and assessment/verification timestamps;
- the M4.18/M4.19-derived fingerprints already present in M4.20;
- the M4.20 assessment fingerprint;
- the M4.21 verification fingerprint;
- the fail-closed readiness state and blocker codes.

The persistence boundary does not rebuild the M4.20 assessment. Reloading a stored row reconstructs the assessment and verification receipt and rechecks both fingerprints.

Duplicate writes of the same verification fingerprint are idempotent; no update or delete operation is exposed by the repository.

## API

GET /api/v1/integration-execution/readiness

The endpoint requires the existing evidence.read permission at ministry scope and returns only a previously persisted, independently verified receipt. Optional filters allow an exact candidate SHA and target environment.

A missing receipt returns 404; an invalid persisted receipt returns 409.

## Safety boundary

M4.22 is read-only at the HTTP boundary. It does not execute SINA, treasury, bank, tax or insurance providers, use provider credentials, authorize payment, or create staging/pilot evidence. A persisted ready value remains software-side evidence and does not grant production authority.
