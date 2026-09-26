# M3.13 — Snapshot-Driven Retroactive Recalculation & Historical Replay

## Scope

M3.13 hardens the historical payroll boundary around the immutable `PersonnelSnapshotRecord` already present in Morva. A historical payroll artifact must be replayable only when its employee, period and snapshot identity/hash remain consistent with the persisted snapshot.

Retroactive reconciliation now requires a persisted original artifact and revised artifact for every requested period. Both artifacts must reference the **same immutable personnel snapshot** for that period. Their persisted net outputs are compared deterministically; no current HR state, current personnel record, or unapproved legal rule is substituted silently.

## Explicit retroactive order-gap contract

Personnel orders retain `issue_date` (administrative issuance) and `effective_date` (business effect) as separate fields. Gate 1 adds an independent domain contract in `src/morva/payroll/retro_gap.py`:

- detect when `effective_date < issue_date`;
- expose the exact gap in days and the order/employee provenance;
- map the gap to payroll periods through caller-supplied period windows, so Jalali period semantics are not guessed by the engine;
- require both original and revised persisted outputs for every affected period;
- compute signed net arrears and positive payable arrears with `Decimal`;
- emit immutable audit evidence containing actor, timestamp, reason, before/after totals and a deterministic SHA-256 fingerprint.

The module deliberately does not infer statutory rates, thresholds, eligibility or deductions. It compares governed historical outputs only.

## Fail-closed invariants

1. Missing historical snapshot blocks replay and retroactive reconciliation.
2. Snapshot employee/period mismatch blocks replay and retroactive reconciliation.
3. Snapshot hash mismatch blocks replay and retroactive reconciliation.
4. A retro period missing either the original or revised persisted artifact is rejected.
5. Original and revised artifacts for a historical period must share one immutable snapshot.
6. Period keys are validated as `YYYY-MM` with months `01..12`.
7. A personnel order with `issue_date < effective_date` is rejected by the domain contract.
8. An order with `effective_date < issue_date` produces a detected retroactive gap.
9. A detected gap with missing period output fails closed.
10. No legal rate, threshold or formula is inferred or activated by the retro-gap module.

## Historical replay

`replay_artifact()` proves snapshot provenance before reconstructing the persisted payslip lines and recalculating the fingerprint/output hash. The returned evidence includes the historical snapshot id/hash and rule-pack version.

## Snapshot-driven retro

`calculate_snapshot_driven_retro()` is the existing provenance/reconciliation boundary over persisted payroll artifacts. `calculate_gap_arrears()` is the complementary date-gap contract for explicitly supplied original/revised period outputs.

## Certification boundary

This tranche provides deterministic software controls and tests. It does **not** certify any legal payroll treatment, activate rates/formulas, or constitute production historical replay certification. A certified historical replay corpus still requires authoritative legal-rule evidence, approved population-specific rule packs, representative historical data, and independent finance/legal validation.
