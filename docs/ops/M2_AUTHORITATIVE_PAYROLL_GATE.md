# Morva M2 — Authoritative Payroll Calculation & Reconciliation

## Implemented

1. A production rule-pack manifest parser and hard gate now reject synthetic, unapproved, or incomplete 1405 packs.
2. Payroll can be calculated from effective-dated `RuleEngine` definitions with the selected rule-pack version carried into `PayrollResult`.
3. A deterministic synthetic 1405 golden scenario exercises the rule-driven calculation path.
4. Three-way payroll/accounting/payment reconciliation has a hard release stop on batch, employee-count, gross, deduction, or net mismatch.
5. External payroll transfer payloads now have a contract for batch ID, correlation ID, balanced totals, and SHA-256 payload evidence.
6. CI contains an explicit M2 gate covering the golden payroll flow, reconciliation stop conditions, and integration contract.

## Certification blockers

The repository intentionally does **not** assert Iranian legal rates or thresholds without authoritative evidence. The operational 1405 manifest therefore remains `pending_authoritative_sources` until each required component is backed by approved source documentation and evidence hashes.

Integration code is contract-ready, but production staging evidence for SINA, treasury/accounting, bank, tax, and insurance endpoints still has to be supplied by their actual environments.

The synthetic golden suite is a development certification harness only. Its rates are deliberately not legal claims and must not be promoted to production.

## Release gate

Production payroll release is blocked until all of the following are true:

- the authoritative 1405 manifest passes `RulePackManifest.assert_production_ready()`;
- calculation rules are sourced from an approved rule pack;
- golden/regression evidence is green;
- three-way reconciliation passes exactly;
- integration contracts pass in staging with real endpoint evidence;
- security, DR/recovery, and performance evidence have been recorded.
