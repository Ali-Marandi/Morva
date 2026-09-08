# M3.10 Personnel Order Lifecycle

This tranche hardens the personnel-order lifecycle and approval evidence without authorizing real payroll or payment operations.

## Lifecycle

1. Draft order is validated and persisted idempotently.
2. Submission creates immutable submission provenance.
3. Final approval or rejection requires a distinct decision actor.
4. Rejection requires an explicit reason.
5. A final decision is immutable and cannot be replaced by another decision.
6. Effective personnel-order queries include approved orders only.
7. Submission and decision events are written to the hash-linked audit ledger.

## Evidence

Approval evidence retains the order identity, submitting actor, deciding actor, decision, decision time, and any rejection reason. Missing submission provenance blocks a decision; rejected orders never enter the effective-order set.
