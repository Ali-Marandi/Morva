# Morva Payroll Platform — Delivery Roadmap

**Canonical branch:** `main`  
**Current position:** enterprise validation candidate; not production-certified for real payroll/payment.

## Completed implementation foundations

- Modular-monolith structure and API v1 boundary
- Decimal-safe payroll calculator and reproducible fingerprints
- Effective-dated rule and Rule Pack foundations with fail-closed legal readiness
- Persisted PayrollRun and canonical payroll lifecycle
- Caller-supplied authoritative calculation disabled
- Import manifest, checksum, provenance and quarantine foundations
- Effective PersonnelSnapshot and source-to-payroll provenance
- Persisted employee payroll artifacts and ordered payslip lines
- Persistent hash-linked audit ledger and verification
- OIDC/JWT boundary, hierarchical authorization, MFA and SoD controls
- Transactional Outbox/Inbox, integration receipts and idempotency foundations
- Payment-batch and encrypted beneficiary-account foundations
- Bank receipt and exact amount reconciliation foundations
- PostgreSQL/Alembic production schema gate
- RTL web distribution through GitHub Pages
- CI for Python 3.12/3.13, PostgreSQL, migrations, Ruff, pytest, dependency audit and web build
- Living implementation, production-readiness and prompt-compliance documentation
- M3.12 ledger treatment governance boundary with explicit fail-closed classification and approval evidence requirements
- M3.13 snapshot-driven retro/replay provenance boundary with immutable historical snapshot binding and dedicated CI gate
- M3.14 authenticated operational dashboard/employee views with explicit API loading/error/empty states
- M3.15 authenticated employee self-service, objection/case persistence and artifact-bound payslip PDF endpoint with dedicated CI gate
- M3.16 employee self-service UX hardening with payslip detail/provenance presentation, period filtering, resilient PDF download handling and dedicated web quality gate
- M3.17 authoritative master-data integrity hardening across organization/personnel assignment, attendance and persisted teacher-rank provenance controls

## Current execution queue

1. Keep exact `main` head green across compilation, Ruff, PostgreSQL migrations, pytest, pip-audit and web build.
2. Refresh the technical assessment after each material implementation tranche. **M3.16/M3.17 refresh recorded in `docs/ASSESSMENT_2026-09-09.md`.**
3. Complete authoritative organization/personnel/rank/attendance master data. **M3.17 strengthened referential, temporal and workflow-integrity gates; authoritative source confirmation and complete population evidence remain pending.**
4. Complete personnel-order lifecycle and approval evidence.
5. Complete legal component matrix and annual Rule Packs from primary sources.
6. Complete tax, pension, insurance, loans and judicial-deduction ledgers with approved treatments. **M3.12 governance boundary is implemented; authoritative treatment evidence and approved population-specific rules remain pending.**
7. Complete snapshot-driven retroactive recalculation and certified historical replay corpus. **M3.13 software provenance/reconciliation controls are implemented; authoritative historical replay corpus and certification evidence remain pending.**
8. Remove remaining demonstration-only frontend behavior and wire operational views to authenticated APIs. **M3.14 completed for the primary dashboard/employee views.**
9. Complete employee self-service, objection/case management and production PDF/reporting. **M3.15 foundation and M3.16 UX hardening implemented: authenticated self-service profile/payslips/orders, artifact-bound PDF download, persistent employee cases, payslip detail/provenance view, period filter and resilient download UX. Identity-directory reconciliation, broader reporting, document-template certification and enterprise grievance policy/SLA evidence remain pending.**
10. Implement official SINA, accounting, treasury, bank, tax and insurance adapters only from authoritative contracts.
11. Run staging tests for every adapter and at least one pilot environment where authorized.
12. Complete end-to-end three-way reconciliation: Morva entitlement ↔ Treasury/PFM instruction ↔ Bank settlement.
13. Implement payment reversal/return handling and settlement exception workflows.
14. Complete production key-management, encryption-at-rest, secret rotation and retention controls.
15. Execute encrypted backup, WAL/PITR restore and disaster-recovery drills with recorded RTO/RPO evidence.
16. Execute target-scale load/concurrency, mutation and financial property-based tests.
17. Complete independent security assessment and close critical findings.
18. Obtain formal finance/legal/operations certification; then produce the matching software tag, GitHub Release, artifacts and deployment evidence.

## Production gate

Morva must not be used for real payroll or real payment until all applicable legal, authoritative-data, integration, security, operational, reconciliation, load and recovery evidence is complete and formally approved.
