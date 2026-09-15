# Morva — Technical & Production Assessment Refresh

**Assessment date:** 2026-09-14  
**Repository:** `Ali-Marandi/Morva`  
**Canonical branch:** `main`  
**Assessment basis:** post-M3.26 snapshot replay certification and M3.27 three-way reconciliation release boundary

> **Safety statement:** This is an engineering assessment only. It does not certify Morva for real payroll or payment. Legal rules, authoritative data, external adapters and organizational authority remain subject to formal evidence and approval.

## Executive assessment

M3.26 established a fail-closed certification boundary for snapshot-driven payroll replay, binding personnel snapshot, Rule Pack, input/output hashes, timezone-aware provenance and independent review/approval before execution readiness.

M3.27 strengthens the payment release trust boundary with explicit three-way reconciliation across the Morva payroll result, the accounting/Treasury-side representation and the payment-side representation. The software gate blocks release whenever batch identity, employee count or gross/deductions/net amounts diverge.

The platform remains an **enterprise validation candidate**, not a production-authorized payroll/payment system. The largest remaining gaps are authoritative source/population evidence, formal legal and organizational approvals, live SINA/accounting/treasury/bank/tax/insurance adapters, staging/pilot evidence, reversal/return workflows, production key/retention controls, DR/load/security evidence and formal certification.

## Maturity snapshot

| Area | Current assessment | Direction |
|---|---:|---|
| Architecture/domain foundations | 8.5/10 | stable |
| Payroll calculation foundation | 8/10 | stable; trust-boundary coverage continues |
| Reconciliation/import foundation | 9/10 | strengthened by M3.27 hard-stop boundary |
| Legal governance | 8.5/10 | governance strong; authoritative approval evidence pending |
| Security/IAM enforcement | 5/10 | endpoint-wide and enterprise IAM evidence pending |
| Persistence/workflow durability | 6.5/10 | improved; production workflow evidence pending |
| External integrations | 4/10 | unchanged; production adapters pending |
| Web product readiness | 8/10 | stable |
| Master-data integrity | 8.5/10 | controls strong; source confirmation/population evidence pending |
| Production/DR readiness | 5/10 | unchanged; operational evidence pending |
| Overall | **~7.4/10** | validation candidate, not production-certified |

These scores are engineering judgements, not compliance certifications.

## Materially reduced findings

- Snapshot replay now has an explicit fail-closed certification boundary with deterministic provenance.
- Three-way release reconciliation now has a dedicated hard-stop software contract and focused regression coverage.
- Existing payment/accounting reconciliation foundations are now tied to a single explicit releaseability boundary rather than relying on integration-specific checks alone.

## Remaining high-priority gaps

1. Authoritative organization/personnel/rank/attendance source confirmation and complete approved population evidence.
2. Official personnel-order schema and real organizational approval policy confirmation with formal sign-off.
3. Primary-source annual legal Rule Packs and population-specific tax/pension/insurance/deduction treatments with formal approval.
4. Authoritative historical replay corpus, certified retro cases and approval evidence.
5. Production SINA/accounting/treasury/bank/tax/insurance adapters and authorized staging/pilot connectivity.
6. Live three-way reconciliation evidence using authoritative external settlement data, plus payment reversal/return exception workflows.
7. Production key management, encryption-at-rest, secret rotation, retention and DR/PITR drills.
8. Target-scale load/concurrency, financial property-based tests and independent security assessment.
9. Formal finance/legal/operations certification and controlled production release evidence.

## Production position

Green CI establishes engineering integrity for the tested paths; it is not production authorization. Real payroll and payment remain fail-closed until the applicable legal, authoritative-data, integration, reconciliation, security, recovery and operational gates are evidenced and formally approved.
