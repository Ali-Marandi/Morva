# M4.87 — Historical Integrity Graph Validator

M4.87 adds an executable graph validator over the M4.86 machine-readable integrity manifest.

## Graph guarantees

- The manifest contains exactly the guarded M4.77–M4.81 layers.
- Every dependency that resolves to another guarded layer points to an earlier layer.
- The resolved layer graph is acyclic.
- The declared sequence is complete, unique and matches the expected M4.77 → M4.78 → M4.79 → M4.80 → M4.81 progression.

External/shared dependencies remain outside the guarded layer graph and are still enforced through the manifest's explicit required-module lists and primitive-adoption guard.

## Enforcement

A dedicated M4.87 CI workflow runs Ruff and the graph contract together with the M4.85 manifest-driven dependency tests.

## Boundary

M4.87 changes no runtime behavior, persistence schema, API contract, fingerprint payload or blocker semantics.
