# M4.17 — Evidence Role Bindings

M4.17 persists certification-role binding receipts so the M4.12 convergence assessment can consume real accepted evidence bindings.

## Contract

- Each binding uses one canonical certification role and its canonical source type.
- Only current, accepted and non-expired evidence may be bound.
- Binding is tied to the exact filtered M4.14 registry fingerprint.
- The binding actor must be distinct from the evidence submitter and approver.
- Non-ministry principals are restricted to their exact organization scope.
- A role may have one binding for a given current registry and scope; historical bindings remain immutable.
- A changed registry fingerprint requires a fresh role binding, preventing stale evidence from satisfying current convergence.
- The persisted record becomes an M4.12 `EvidenceBindingReceipt` without changing the earlier evidence submission or registry records.

## Endpoints

- `POST /api/v1/evidence-submissions/bindings`
- `GET /api/v1/evidence-submissions/bindings`

## Safety

Role binding is an evidence-governance operation only. It does not alter authoritative source documents, execute integrations, activate production, release payments or grant production certification.
