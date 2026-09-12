# Morva — Technical & Production Assessment Refresh

**Assessment date:** 2026-09-12  
**Repository:** `Ali-Marandi/Morva`  
**Canonical branch:** `main`  
**Assessment basis:** post-M3.16 merge plus M3.17/M3.18 governance tranches and authoritative master-data API exposure

> **Safety statement:** This refresh is an engineering assessment only. It does not certify Morva for real payroll or payment. Legal rules, authoritative source status and organizational authority remain subject to formal evidence and approval.

## Executive assessment

M3.14, M3.15 and M3.16 materially closed the previously identified demonstration-only operational web gaps by wiring the primary dashboard/employee surfaces to authenticated APIs and hardening employee self-service payslip detail, period filtering, provenance presentation and PDF failure handling.

M3.17 strengthens the authoritative master-data boundary with fail-closed checks for assignment references, assignment target activity, date-range validity, overlapping assignments, active-employee assignment cardinality, attendance integrity and persisted teacher-rank decision provenance. The authoritative integrity validator is now also exposed through an authenticated API endpoint.

M3.18 closes the software-side personnel-order governance boundary with persisted, versioned and source-bound organizational approval policy, deterministic policy fingerprinting, exact submission/decision-role enforcement, immutable policy-bound approval evidence and fail-closed effective-state reconciliation.

The platform remains an **enterprise validation candidate**, not a production-authorized payroll/payment system. The principal remaining risks are authoritative population/source confirmation, official personnel-order schema and real organizational approval policy evidence, legal Rule Pack approval, population-specific ledger treatments, certified historical replay corpus, official external adapters and staging/pilot evidence, end-to-end reconciliation, reversal/exception workflows, production key/retention controls, DR/load/security evidence and formal certification.

## Maturity snapshot

| Area | Current assessment | Direction |
|---|---:|---|
| Architecture/domain foundations | 8.5/10 | stable |
| Payroll calculation foundation | 8/10 | stable; production trust-boundary work remains broader |
| Reconciliation/import foundation | 8.5/10 | strengthening |
| Legal governance | 8.5/10 | governance strong; authoritative approval evidence pending |
| Security/IAM enforcement | 5/10 | endpoint-wide enforcement and enterprise IAM evidence remain pending |
| Persistence/workflow durability | 6.5/10 | improved by M3.15/M3.16 and M3.18 evidence controls; full production workflow evidence pending |
| External integrations | 4/10 | unchanged; production adapters pending |
| Web product readiness | 8/10 | materially improved by M3.14–M3.16 |
| Master-data integrity | 8.5/10 | M3.17 controls plus authenticated authoritative-integrity API; source confirmation/population evidence pending |
| Production/DR readiness | 5/10 | unchanged; operational evidence pending |
| Overall | **~7.2/10** | validation candidate, not production-certified |

These scores are engineering judgements, not compliance certifications.

## Closed or materially reduced findings

- **Frontend fabricated operational state:** primary dashboard/employee views now use authenticated API data with explicit loading/error/empty handling (M3.14).
- **Employee self-service foundation:** authenticated profile, payslip/order views, objection/case persistence and artifact-bound PDF support implemented (M3.15).
- **Payslip UX resilience:** period filtering, detailed provenance/explanation presentation and resilient PDF download/error lifecycle implemented (M3.16).
- **Master-data referential/temporal integrity:** assignment target activity, invalid ranges, overlap and active-employee assignment cardinality are now blocking checks (M3.17).
- **Authoritative master-data access:** fail-closed authoritative validator is exposed through an authenticated `/api/v1/master-data/authoritative-integrity` endpoint with dedicated API regression coverage.
- **Attendance integrity:** employee reference, period, workflow status, non-negative units, source fingerprint and approval evidence are blocking checks.
- **Teacher-rank persisted provenance:** decision/appeal states remain blocked when persisted decision provenance is missing or tampered.
- **Personnel-order governance:** M3.18 adds immutable order/policy fingerprints, persisted organizational approval policy provenance, exact role enforcement, separation of duties, mandatory rejection reason and fail-closed effective-state reconciliation.

## Remaining high-priority gaps

1. Authoritative organization/personnel/rank/attendance source confirmation and complete approved population evidence.
2. Official personnel-order schema and real organizational approval policy confirmation with formal sign-off.
3. Primary-source annual legal Rule Packs and population-specific tax/pension/insurance/deduction treatments with formal approval.
4. Snapshot-driven historical replay corpus and certification evidence.
5. Production SINA/accounting/treasury/bank/tax/insurance adapters and staging/pilot connectivity.
6. End-to-end three-way reconciliation and payment reversal/return exception workflows.
7. Production key management, encryption-at-rest, secret rotation, retention and DR/PITR drills.
8. Target-scale load/concurrency, financial property-based tests and independent security assessment.
9. Formal finance/legal/operations certification and controlled production release evidence.

## Production position

Green CI indicates engineering integrity for the tested paths; it is not a production authorization. Real payroll and payment must remain fail-closed until the documented production gates and formal approvals are evidenced.
