# M4.25 Readiness Organization Scope Binding

M4.25 binds persisted integration-execution readiness verification receipts to an exact organization scope without changing the independent M4.21 verification fingerprint.

## Scope model

Supported organization scopes are:

- `school`
- `district`
- `province`
- `ministry`

Every persisted receipt stores:

- `organization_scope`
- `organization_scope_id`
- `scope_binding_fingerprint`

The scope binding fingerprint is a separate SHA-256 identity derived from the already verified M4.21 verification fingerprint plus the normalized scope and scope ID:

`readiness-scope-binding:v1:<verification_fingerprint>:<scope>:<scope_id>`

This keeps M4.21 independent of authorization scope while preventing post-verification scope reassignment.

## API behavior

The current readiness and history APIs accept optional scope filters.

A ministry principal may omit the scope filter to read across all persisted scopes or select an exact scope and ID.

A non-ministry principal is always constrained to its own `scope + scope_id`. Supplying another scope returns `403`.

Persisted scope-binding fingerprint mismatches fail closed with `409`.

## Migration behavior

Migration `0026_integration_readiness_scope_bindings` adds the three scope columns, backfills existing M4.22 receipts to the legacy `ministry/ministry` scope, computes their deterministic scope-binding fingerprints, then enforces non-null values and a unique scope-binding index.

The migration uses Alembic batch operations so the same migration path remains compatible with the repository's SQLite migration gate as well as PostgreSQL.

## Safety boundary

M4.25 performs no external provider execution, credential use, payroll calculation, payment mutation or production authorization. Scope binding is an authorization and audit-integrity control over already persisted software-side readiness evidence.
