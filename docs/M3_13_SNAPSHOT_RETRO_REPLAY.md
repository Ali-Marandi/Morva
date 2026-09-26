# M3.13 — Snapshot-Driven Retroactive Recalculation & Historical Replay

## Scope

M3.13 hardens the historical payroll boundary around the immutable `PersonnelSnapshotRecord` already present in Morva. A historical payroll artifact must be replayable only when its employee, period and snapshot identity/hash remain consistent with the persisted snapshot.

Retroactive reconciliation requires a persisted original artifact and revised artifact for every requested period. Both artifacts must reference the **same immutable personnel snapshot** for that period. Their persisted net outputs are compared deterministically; no current HR state, current personnel record, or unapproved legal rule is substituted silently.

## Administrative arrears-gap detection

A personnel order keeps its administrative `issue_date` separate from its legal `effective_from` date. `detect_arrears_gap()` is a deterministic domain helper that reports the calendar-day gap when issuance occurs after legal effect.

این تشخیص فقط وجود و طول شکاف را مشخص می‌کند؛ مبلغ مابه‌التفاوت، نرخ قانونی یا استحقاق پرداخت از تاریخ‌ها استنتاج نمی‌شود و باید از artifactهای اصلی/اصلاحی و Rule Pack معتبر به دست آید.

## Fail-closed invariants

1. Missing historical snapshot blocks replay and retroactive reconciliation.
2. Snapshot employee/period mismatch blocks replay and retroactive reconciliation.
3. Snapshot hash mismatch blocks replay and retroactive reconciliation.
4. A retro period missing either the original or revised persisted artifact is rejected.
5. Original and revised artifacts for a historical period must share one immutable snapshot.
6. Period keys are validated as `YYYY-MM` with months `01..12`.
7. An issue date earlier than the effective date is rejected by arrears-gap detection.
8. No legal rate, threshold or formula is inferred or activated by M3.13.

## Historical replay

`replay_artifact()` proves snapshot provenance before reconstructing persisted payslip lines and recalculating the fingerprint/output hash. Returned evidence includes the historical snapshot identity and rule-pack version.

## Snapshot-driven retro

`calculate_snapshot_driven_retro()` is a provenance/reconciliation boundary over persisted payroll artifacts. It intentionally consumes persisted original/revised outputs rather than recalculating against today's personnel state. Result periods retain both artifact snapshot ids and rule-pack versions for auditability.

## Certification boundary

This tranche provides deterministic software controls and tests. It does **not** certify any legal payroll treatment, activate rates/formulas, or constitute production historical replay certification. A certified historical replay corpus still requires authoritative legal-rule evidence, approved population-specific rule packs, representative historical data, and independent finance/legal validation.
