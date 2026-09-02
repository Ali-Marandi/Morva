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

## Current execution queue

1. Keep exact `main` head green across compilation, Ruff, PostgreSQL migrations, pytest, pip-audit and web build.
2. Refresh the technical assessment after each material implementation tranche.
3. Complete authoritative organization/personnel/rank/attendance master data.
4. Complete personnel-order lifecycle and approval evidence.
5. Complete legal component matrix and annual Rule Packs from primary sources.
6. Complete tax, pension, insurance, loans and judicial-deduction ledgers with approved treatments.
7. Complete snapshot-driven retroactive recalculation and certified historical replay corpus.
8. Remove remaining demonstration-only frontend behavior and wire operational views to authenticated APIs.
9. Complete employee self-service, objection/case management and production PDF/reporting.
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
