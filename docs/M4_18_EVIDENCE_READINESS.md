# M4.18 — Evidence Readiness

M4.18 connects persisted M4.17 role bindings to the M4.12 convergence assessment and produces an explicit remediation view.

## Contract

- Readiness is evaluated only from the current accepted evidence registry.
- Persisted role bindings must match the current registry fingerprint.
- Superseded evidence is blocked even when a historical binding remains present.
- Each blocked certification role gets exactly one deterministic remediation item.
- Missing bindings, missing evidence, superseded evidence and population mismatches are explicit machine-readable states.
- The assessment is fingerprinted and includes the registry, convergence and lifecycle identities that produced it.
- The API is read-only and performs no production activation, external provider call or payment operation.

## Endpoint

- `GET /api/v1/evidence-submissions/readiness`

## Safety

This is an operational visibility and remediation layer. It does not constitute legal, finance, security or production certification by itself.
