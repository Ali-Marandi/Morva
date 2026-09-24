# Morva Payroll Platform Architecture

## Mission

Morva is a payroll and personnel platform for public-sector education organizations. The domain is designed around traceability, effective dates, legal-rule versioning and reproducible calculations.

## What is real vs. governance scaffolding

Real persisted application paths currently execute for:
- payroll lifecycle transitions: `src/morva/payroll/lifecycle.py`;
- effective-dated safe Rule Engine evaluation: `src/morva/rules/engine.py`;
- Decimal payroll calculation: `src/morva/payroll/calculator.py`;
- JWT/OIDC authentication and scoped authorization: `src/morva/security/auth.py`, `src/morva/security/policy.py`;
- AES-GCM field encryption and versioned key derivation: `src/morva/security/field_crypto.py`.

Fail-closed governance scaffolding remains for authoritative legal rates/population matrices, official adapter credentials/endpoints, ministry master-data acceptance, KMS/HSM custody and operational rotation evidence, target-environment DR/load evidence, and final legal/finance/security/operations certification. See [`docs/IMPLEMENTATION_MATRIX.md`](IMPLEMENTATION_MATRIX.md) for the canonical implementation status.

## Field encryption key derivation

New field ciphertexts use HKDF-SHA256 to derive a 32-byte AES-256 key with an explicit key-version context. The public API remains `key_material` plus optional `key_version`; existing unversioned ciphertexts continue to decrypt using the legacy SHA-256 derivation so stored values can be migrated by normal decrypt-and-reencrypt flow.

`key_material` must remain a high-entropy, centrally managed secret. It must never be a user-supplied password, passphrase or other low-entropy credential.

## Bounded contexts

- `domain`: people, employment, positions and personnel orders.
- `rules`: effective-dated rules and legal references.
- `payroll`: payroll lines, calculation and financial bases.
- `persistence`: SQLAlchemy persistence boundary.
- `api`: HTTP/application boundary.

Planned contexts are taxation, pension, insurance, budgeting, workflow, audit and external integrations.

## Non-negotiable invariants

1. Money uses `Decimal`; floating point is forbidden for payroll arithmetic.
2. Personnel orders have issue and effective dates; history is never overwritten.
3. Every payroll result carries a ruleset version.
4. Every earning can declare tax, pension and insurance treatment.
5. A legal rule must have an effective period before production use.
6. External integrations remain adapters and cannot own payroll domain decisions.
7. AI may detect anomalies or assist explanations, but it never becomes the legal source of truth.

## Production target

The first production-grade deployment should use PostgreSQL, migrations, RBAC, MFA, immutable audit events, approval workflows, encrypted backups and an isolated worker for large payroll runs.
