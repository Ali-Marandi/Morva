# M3.17 / M3.18 Personnel Order Lifecycle & Approval Governance

M3.17 hardens personnel-order lifecycle evidence without manufacturing legal authority. A personnel order is immutable after registration; approval/rejection is a separate append-only decision; effective-state reads require an approved decision.

M3.18 closes the remaining software-side governance boundary by requiring a persisted, approved organizational approval policy before submission or final decision. The policy is versioned, source-bound and fingerprinted; actor roles are checked against that policy and the policy fingerprint is carried into submission and decision evidence.

## Controls

- registration captures an immutable order fingerprint over identity, dates, reference and line payload;
- registration is idempotent only when the submitted order content matches the stored fingerprint;
- submission provenance identifies the actor and role who submitted the order for approval;
- submission requires an explicitly identified, persisted and approved organizational approval policy;
- the approval policy records its version, covered order types, required submission role, required decision role, authoritative source reference and source hash;
- the approval policy itself has a deterministic SHA-256 fingerprint and any tampering fails closed;
- final approval/rejection is single-write and immutable;
- separation of duties requires submitter and decision-maker to be distinct;
- the decision-maker role must match the approved policy;
- rejection requires a non-empty reason;
- approval evidence is bound to the exact registered order fingerprint and approval-policy fingerprint;
- effective-state reconciliation now returns an explicit blocked/reconciled result and never silently drops an approved order whose order, submission or policy evidence is missing or inconsistent;
- effective orders are accepted only when the stored approval evidence matches the current order record and policy evidence;
- tampering, missing policy evidence or fingerprint mismatch fails closed and cannot become effective payroll state.

## Evidence

The automated M3.17/M3.18 gate covers registration idempotency, tamper detection, approval SoD, mandatory rejection reason, immutable final decision, policy approval status, policy coverage, exact role enforcement, policy fingerprint integrity and fail-closed effective-state reconciliation.

This gate establishes software control evidence only. The actual organizational approval policy, authorized roles, official personnel-order schema and competent ministry/organizational authority still require authoritative source confirmation and formal sign-off. Until those are supplied, the system remains an enterprise-validation candidate rather than production-certified payroll/payment software.
