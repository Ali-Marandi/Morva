# M4.88 — Manifest-to-Source Consistency

M4.88 closes a governance gap in M4.87: the graph validator proves the graph declared by the manifest, while M4.88 verifies that the guarded source and test files actually implement the dependency declarations in that manifest.

## Guarantees

- Every manifest-declared source dependency is present in the corresponding source imports.
- No guarded M4.77–M4.81 module is imported by a guarded layer without being declared in the manifest.
- Declared source and test paths exist.
- Manifest-declared test dependencies are present in the corresponding test imports.

## Boundary

M4.88 is a static architecture/readiness guard. It changes no runtime behavior, persistence schema, API contract, fingerprint payload, blocker semantics or production authority.
