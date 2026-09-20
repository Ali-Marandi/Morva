# M3.84 — Integration Execution Evidence Contract

M3.84 defines the evidence format for an authorized staging/pilot execution of all six
official adapter boundaries.

Each adapter result is bound to the exact candidate SHA, target environment, immutable
evidence digest, execution timestamps and an operator identity. The receipt is deterministic
and write-once.

The contract does not execute adapters, contact provider endpoints, activate credentials,
or authorize production. Real execution evidence must come from an authorized external
staging/pilot run.
