# M4.14 — Evidence Registry Bridge

M4.14 bridges accepted M4.13 evidence submissions into the M4.1 authoritative evidence registry model.

## Contract

- Only submissions with status `accepted` can enter the registry projection.
- The persisted M4.13 submission fingerprint is verified before conversion.
- The M4.1 `AuthoritativeEvidenceItem` contract remains authoritative for source type, URI, SHA-256, scope and validity metadata.
- Approval metadata is preserved as `approved_by` and `approved_at`.
- The projected registry is sorted deterministically and exposes the exact M4.1 registry fingerprint.
- Pending and rejected submissions remain outside the registry and cannot satisfy M4.2 closure roles.
- The read-only API projection is organization-scope filtered; ministry principals may view the ministry-wide accepted projection.
- Projection is not production certification and performs no external upload, activation, provider call or production mutation.

## Flow

`M4.13 accepted submission → fingerprint verification → M4.1 item mapping → deterministic registry projection → M4.12 convergence input`

The projection is intentionally derived from the accepted submission records rather than treating an API decision as automatic production authorization.
