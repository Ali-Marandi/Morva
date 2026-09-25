[![Lint](https://github.com/Ali-Marandi/Morva/actions/workflows/lint.yml/badge.svg?branch=main)](https://github.com/Ali-Marandi/Morva/actions/workflows/lint.yml)
[![Tests](https://github.com/Ali-Marandi/Morva/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/Ali-Marandi/Morva/actions/workflows/tests.yml)
[![Migrations](https://github.com/Ali-Marandi/Morva/actions/workflows/migrations.yml/badge.svg?branch=main)](https://github.com/Ali-Marandi/Morva/actions/workflows/migrations.yml)
[![pip-audit](https://github.com/Ali-Marandi/Morva/actions/workflows/pip-audit.yml/badge.svg?branch=main)](https://github.com/Ali-Marandi/Morva/actions/workflows/pip-audit.yml)
[![Web Build](https://github.com/Ali-Marandi/Morva/actions/workflows/web-build.yml/badge.svg?branch=main)](https://github.com/Ali-Marandi/Morva/actions/workflows/web-build.yml)

**Default branch:** `main`  
**Public repository:** `Ali-Marandi/Morva`  
**Public web:** `https://ali-marandi.github.io/Morva/`  
**License:** MIT — contributions and forks are welcome for engineering, research, documentation and governance work within `CONTRIBUTING.md`.

## What is real vs. governance scaffolding

Morva has real persisted application paths today for:
- canonical payroll lifecycle state transitions in `src/morva/payroll/lifecycle.py`;
- effective-dated safe rule evaluation in `src/morva/rules/engine.py`;
- Decimal-based payroll calculation in `src/morva/payroll/calculator.py`;
- JWT/OIDC authentication and scoped authorization in `src/morva/security/auth.py` and `src/morva/security/policy.py`;
- AES-GCM field encryption with versioned key derivation in `src/morva/security/field_crypto.py`.

The following remain explicitly fail-closed governance/operations boundaries rather than invented production authority: authoritative population-specific legal rates and matrices, official external adapter credentials/endpoints, authoritative ministry master-data acceptance, KMS/HSM custody and operational key rotation, target-environment DR/load evidence, and formal legal/finance/security/operations certification. The canonical status lives in [`docs/IMPLEMENTATION_MATRIX.md`](docs/IMPLEMENTATION_MATRIX.md); this section is intentionally only a map.

**Current development baseline (2026-09-24):**
- M4.22–M4.30 establish append-only readiness receipts, scope-bound convergence, explicit freshness policies and registry-bound evaluation.
- M4.31–M4.35 add deterministic registry history/integrity plus registry-bound freshness receipts with fail-closed reconstruction.
- M4.36–M4.40 add immutable historical registry snapshots, historical policy resolution, historical freshness evaluation and append-only historical freshness receipts.
- M4.41 links each historical freshness receipt to its exact M4.37 receipt-to-snapshot binding with independent continuity verification.
- M4.42 exposes deterministic, ministry-managed lineage history with timestamp+UUID cursors, exact receipt/binding/snapshot filters and per-record source re-verification.
- M4.43 independently reconstructs the M4.36→M4.37→M4.40→M4.41 identity chain and returns deterministic verified/blocked status plus a chain fingerprint through a read-only API.
- M4.44 persists those chain-verification results as fingerprint-idempotent receipts, provides ministry-managed cursor history and a direct receipt re-verification API.
- M4.45 independently compares persisted M4.44 receipt identity with a separately reconstructed historical chain and exposes a deterministic verification fingerprint.
- M4.46 persists those independent-verification results as fingerprint-idempotent evidence with ministry-managed history and re-verification.
- Release/security hardening adds version consistency checks, HKDF-based new field-encryption derivation with legacy decrypt compatibility, independent-review hooks, a reproducible local verification script and externally visible CI badges.
- This entire M4 freshness/history line is governance/readiness metadata only; no provider execution or production authority is created.
- CI and release gates remain fail-closed for any real payroll/payment authority.

**Latest Changes (v1.0.1):**
- ✅ Security dependency update: `cryptography` 50.x
- ✅ Python 3.12/3.13 CI green
- ✅ `pip-audit` green
- ✅ Web production build green
- ✅ Canonical payroll lifecycle regression test aligned

The current codebase contains the enterprise payroll foundation: persisted payroll artifacts and payslip lines, effective-dated personnel/master-data foundations, legal Rule Pack governance, hierarchical authorization, encrypted sensitive-field primitives, lifecycle audit, transactional Outbox/Inbox, payment-batch controls, reconciliation foundations, historical replay, PostgreSQL migrations, automated tests, CI/CD pipeline and **world-class web platform**.