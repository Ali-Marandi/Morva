**Default branch:** `main`  
**Public repository:** `Ali-Marandi/Morva`  
**Public web:** `https://ali-marandi.github.io/Morva/`

**Current development baseline (2026-09-24):**
- M4.22–M4.30 establish append-only readiness receipts, scope-bound convergence, explicit freshness policies and registry-bound evaluation.
- M4.31–M4.35 add deterministic registry history/integrity plus registry-bound freshness receipts with fail-closed reconstruction.
- M4.36–M4.40 add immutable historical registry snapshots, historical policy resolution, historical freshness evaluation and append-only historical freshness receipts.
- M4.41 links each historical freshness receipt to its exact M4.37 receipt-to-snapshot binding with independent continuity verification.
- M4.42 exposes deterministic, ministry-managed lineage history with timestamp+UUID cursors, exact receipt/binding/snapshot filters and per-record source re-verification.
- M4.43 independently reconstructs the M4.36→M4.37→M4.40→M4.41 identity chain and returns deterministic verified/blocked status plus a chain fingerprint through a read-only API.
- This entire M4 freshness/history line is governance/readiness metadata only; no provider execution or production authority is created.
- CI and release gates remain fail-closed for any real payroll/payment authority.

**Latest Changes (v1.0.1):**
- ✅ Security dependency update: `cryptography` 50.x
- ✅ Python 3.12/3.13 CI green
- ✅ `pip-audit` green
- ✅ Web production build green
- ✅ Canonical payroll lifecycle regression test aligned

The current codebase contains the enterprise payroll foundation: persisted payroll artifacts and payslip lines, effective-dated personnel/master-data foundations, legal Rule Pack governance, hierarchical authorization, encrypted sensitive-field primitives, lifecycle audit, transactional Outbox/Inbox, payment-batch controls, reconciliation foundations, historical replay, PostgreSQL migrations, automated tests, CI/CD pipeline and **world-class web platform**.