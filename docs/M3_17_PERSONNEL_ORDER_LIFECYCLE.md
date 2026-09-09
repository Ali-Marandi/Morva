# M3.17 Personnel Order Lifecycle & Approval Evidence

M3.17 hardens personnel-order governance without manufacturing legal authority. A personnel order is immutable after registration; approval/rejection is a separate append-only decision; effective-state reads require an approved decision.

## Controls

- registration captures an immutable order fingerprint over identity, dates, reference and line payload;
- registration is idempotent only when the submitted order content matches the stored fingerprint;
- submission provenance identifies the actor who submitted the order for approval;
- final approval/rejection is single-write and immutable;
- separation of duties requires submitter and decision-maker to be distinct;
- rejection requires a non-empty reason;
- approval evidence is bound to the exact registered order fingerprint;
- effective orders are accepted only when the stored approval evidence matches the current order record;
- tampering or fingerprint mismatch fails closed and cannot become effective payroll state.

## Evidence

The automated M3.17 gate covers registration idempotency, tamper detection, approval SoD, mandatory rejection reason, immutable final decision and effective-state filtering.

This gate establishes software control evidence only. Official personnel-order schemas, ministry authority and organizational approval policy still require authoritative source confirmation.
