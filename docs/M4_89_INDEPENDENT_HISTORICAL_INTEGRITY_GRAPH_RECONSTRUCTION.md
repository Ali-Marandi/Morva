# M4.89 — Independent Historical Integrity Graph Reconstruction

M4.89 validates that the graph declared by the M4.86 integrity manifest matches guarded dependencies independently reconstructed from Python import statements.

## Architectural correction

M4.87 originally mapped only the primary source path for each layer. The M4.77 capability also exposes a persistence module used by M4.78–M4.81, so imports of that module were not represented as M4.77 graph edges.

M4.89 adds explicit `component_modules` aliases to each manifest layer. These aliases identify the source modules that belong to a guarded milestone, including the M4.77 persistence module.

## Independent checks

- Every component-module alias is uniquely assigned to one layer, and each layer's primary source module appears in its aliases.
- Python AST import reconstruction discovers actual guarded cross-layer imports without deriving edges from `required_modules`.
- Observed guarded imports must exactly equal the manifest-declared guarded dependencies.
- The reconstructed graph must be complete, acyclic and ordered backward.
- M4.87 consumes the component aliases so its topology checks include the M4.77 persistence dependency.
- M4.88 fingerprints the expanded component-aware manifest using the shared canonical SHA-256 primitive.

## Fingerprint correction

The previously stored M4.88 fingerprint did not match a recomputation from the manifest projection. M4.89 updates the artifact and the M4.88 regression test to require exact agreement. This prevents stale or manually guessed values from being treated as validated integrity evidence.

## Enforcement

The dedicated M4.89 CI workflow runs independent graph reconstruction, M4.87 graph checks, M4.88 fingerprint verification and M4.85 manifest/dependency tests together.

## Boundary

All changes are architecture/governance checks. No application runtime behavior, persistence schema, API contract, business fingerprint payload or production authority changes.
