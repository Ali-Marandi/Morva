# M4.85 — Repository-Wide Historical Integrity Contract

M4.85 adds an executable repository-wide contract over the M4.77–M4.81 integrity chain.

## Contract scope

- M4.77 runtime dependencies are explicitly bounded to the M4.76 persistence layer.
- M4.78 runtime dependencies explicitly include the M4.77 snapshot, M4.76 source and shared integrity primitive.
- M4.79 persistence explicitly consumes the M4.78 verifier and its M4.76/M4.77 source chain.
- M4.80 explicitly consumes the M4.79 receipt, the M4.77 snapshot, M4.76 source records, M4.78 reconstruction and the shared SHA-256 primitive.
- M4.81 explicitly consumes the M4.79 receipt and M4.80 verifier.
- The contract rejects forward dependencies on unreached M4 layers.
- The contract keeps the focused test for each tranche attached to its expected runtime/persistence symbol.
- The guarded runtimes must not reintroduce local SHA-256 implementations.

## Enforcement

The contract uses Python AST inspection rather than formatting or string-only heuristics for import and dependency assertions. A dedicated CI workflow runs Ruff and the focused integrity-contract suite.

## Boundary

M4.85 changes no persistence schema, API contract, fingerprint payload, blocker code or production authority. It is a structural integrity and regression guard only.
