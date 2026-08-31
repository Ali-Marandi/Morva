# Morva Payroll Platform Architecture

## Mission

Morva is a payroll and personnel platform for public-sector education organizations. The domain is designed around traceability, effective dates, legal-rule versioning and reproducible calculations.

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
