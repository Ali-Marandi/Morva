# M3.21 — 1405 Primary-Source Evidence Contract

## Purpose

M3.21 establishes the software boundary for importing 1405 legal and payroll evidence from primary sources without embedding guessed rates or treatments in the repository.

## Evidence contract

Every production-bound source artifact must provide:

- a stable source identifier and legal citation;
- the issuing authority;
- an absolute HTTPS source URI;
- the exact artifact SHA-256;
- adoption and effective dates;
- retrieval timestamp for provenance;
- distinct review and approval evidence in the existing RuleEvidence flow;
- regression evidence before activation.

`validate_primary_source_evidence()` performs the deterministic structural checks. A structurally valid artifact is not automatically legally approved; activation remains governed by the existing fail-closed Rule Pack gate.

## 1405 source register

`docs/legal/rule-packs/1405/primary-source-register.yml` maps the existing 1405 component set to four source families already represented by the legal component matrix: Civil Service Management Law, teacher-ranking regulation, 1405 public-sector payroll/payment instructions, and 1405 salary-tax provisions.

The register deliberately leaves the document locator, hash and approval state unresolved until the actual primary artifacts are attached. This prevents a secondary article, prior-year rule, or inferred value from becoming a production rule.

## Verified research inputs

Current external research confirms that the Social Security organization publishes its regulations/circulars on `tamin.ir` and points to `dotic.ir` for consolidated legislation, and a current 1405 Social Security circular exists for the wage basis used for insurance. These are discovery inputs only; the repository does not treat them as approved payroll evidence until the exact primary artifact is captured, hashed and formally reviewed. 

A 1405 budget-execution regulation is also publicly reported as issued by the government, including requirements around registration of personnel/payment information in SINA. The exact primary publication must still be attached to the governed evidence record before activation.

## Non-goals

This tranche does not assert 1405 tax brackets, coefficients, insurance percentages, pension rates, overtime formulas, teacher-ranking amounts, or any other numeric legal treatment. Such values belong only in approved evidence-backed Rule Packs.
