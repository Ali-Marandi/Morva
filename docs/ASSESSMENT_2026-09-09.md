# Morva — Technical & Production Assessment Refresh

**Assessment date:** 2026-09-09  
**Repository:** `Ali-Marandi/Morva`  
**Canonical branch:** `main`  
**Assessment basis:** post-M3.16 merge plus M3.17 authoritative master-data integrity tranche

> **Safety statement:** This refresh is an engineering assessment only. It does not certify Morva for real payroll or payment. Legal rules, authoritative source status and organizational authority remain subject to formal evidence and approval.

## Executive assessment

M3.14, M3.15 and M3.16 materially closed the previously identified demonstration-only operational web gaps by wiring the primary dashboard/employee surfaces to authenticated APIs and hardening employee self-service payslip detail, period filtering, provenance presentation and PDF failure handling.

M3.17 strengthens the authoritative master-data boundary with fail-closed checks for assignment references, assignment target activity, date-range validity, overlapping assignments, active-employee assignment cardinality, attendance integrity and persisted teacher-rank decision provenance.

The platform remains an **enterprise validation candidate**, not a production-authorized payroll/payment system. The principal remaining risks are authoritative population/source confirmation, complete personnel-order evidence, legal Rule Pack approval, population-specific ledger treatments, certified historical replay corpus, official external adapters and staging/pilot evidence, end-to-end reconciliation, reversal/exception workflows, production key/retention controls, DR/load/security evidence and formal certification.

## Maturity snapshot

| Area | Current assessment | Direction |
|---|---:|---|
| Architecture/domain foundations | 8.5/10 | stable |
| Payroll calculation foundation | 8/10 | stable; production trust-boundary work remains broader |
| Reconciliation/import foundation | 8.5/10 | strengthening |
| Legal governance | 8.5/10 | governance strong; authoritative approval evidence pending |
| Security/IAM enforcement | 5/10 | unchanged by M3.17; endpoint-wide enforcement remains pending |
| Persistence/workflow durability | 6/10 | improved by existing M3.15/M3.16 foundations; full payroll workflow evidence pending |
| External integrations | 4/10 | unchanged; production adapters pending |
| Web product readiness | 8/10 | materially improved by M3.14–M3.16 |
| Master-data integrity | 8/10 | materially improved by M3.17; authoritative source confirmation/population evidence pending |
| Production/DR readiness | 5/10 | unchanged; operational evidence pending |
| Overall | **~7.0/10** | validation candidate, not production-certified |

These scores are engineering judgements, not compliance certifications.

## Closed or materially reduced findings

- **Frontend fabricated operational state:** primary dashboard/employee views now use authenticated API data with explicit loading/error/empty handling (M3.14).
- **Employee self-service foundation:** authenticated profile, payslip/order views, objection/case persistence and artifact-bound PDF support implemented (M3.15).
- **Payslip UX resilience:** period filtering, detailed provenance/explanation presentation and resilient PDF download/error lifecycle implemented (M3.16).
- **Master-data referential/temporal integrity:** assignment target activity, invalid ranges, overlap and active-employee assignment cardinality are now blocking checks (M3.17).
- **Attendance integrity:** employee reference, period, workflow status, non-negative units, source fingerprint and approval evidence are blocking checks.
- **Teacher-rank persisted provenance:** decision/appeal states remain blocked when persisted decision provenance is missing or tampered.

## Remaining high-priority gaps

1. Authoritative organization/personnel/rank/attendance source confirmation and complete approved population evidence.
2. Full personnel-order lifecycle with immutable approval evidence and effective-state reconciliation.
3. Primary-source annual legal Rule Packs and population-specific tax/pension/insurance/deduction treatments with formal approval.
4. Snapshot-driven historical replay corpus and certification evidence.
5. Production SINA/accounting/treasury/bank/tax/insurance adapters and staging/pilot connectivity.
6. End-to-end three-way reconciliation and payment reversal/return exception workflows.
7. Production key management, encryption-at-rest, secret rotation, retention and DR/PITR drills.
8. Target-scale load/concurrency, financial property-based tests and independent security assessment.
9. Formal finance/legal/operations certification and controlled production release evidence.

## Production position

Green CI indicates engineering integrity for the tested paths; it is not a production authorization. Real payroll and payment must remain fail-closed until the documented production gates and formal approvals are evidenced.
