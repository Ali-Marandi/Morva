# Morva Rule Pack 1405 Governance

Version family: `1405.x`

This document defines the release contract for the Persian year 1405 Rule Pack. It does not itself assert any legal rate, threshold, coefficient, exemption, or statutory treatment. Those values must be registered from approved primary-source evidence before activation.

## Required activation chain

`1405.x pack -> authoritative legal source -> rule evidence -> calculation-matrix coverage -> regression suite -> distinct review/approval -> readiness gate`

## Required components

- JOB_RIGHT
- INCUMBENT_RIGHT
- JOB_ALLOWANCE
- RANK_ALLOWANCE
- FAMILY_ALLOWANCE
- CHILD_ALLOWANCE
- OVERTIME
- TEACHING_FEE
- TAX
- PENSION
- INSURANCE
- LOAN
- COURT_ORDER

## Fail-closed conditions

A 1405 Rule Pack is not production-activatable when any required component lacks approved primary-source evidence, a calculation-matrix entry, a matching regression-suite fingerprint, or distinct review and approval evidence.

The pack must remain in `review_required`/blocked readiness until those conditions are satisfied.

## Evidence standard

Every executable treatment must identify:

- the issuing authority and source document;
- exact article/clause or equivalent primary-source locator;
- document SHA-256;
- effective-from/effective-to dates;
- population scope;
- executable safe expression or an explicitly non-executable mapping;
- regression-suite SHA-256.

No legacy-software value is considered authoritative merely because it resembles a prior implementation.
