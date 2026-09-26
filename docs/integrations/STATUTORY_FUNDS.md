# Statutory Fund Integration Boundary

## Purpose

Morva keeps the legal treatment and integration boundary of each statutory fund independent. The software does not infer provider rules from observed payroll data.

## Current boundaries

- `StatutoryFund.CENTRAL_CIVIL_SERVANTS_PENSION`
  - Port: `CentralCivilServantsPensionPort`
  - Component namespace: `PENSION`
  - Treatment catalog: independent `StatutoryFundTreatmentCatalog`
- `StatutoryFund.SOCIAL_SECURITY`
  - Port: `SocialSecurityPort`
  - Component namespace: `INSURANCE`
  - Treatment catalog: independent `StatutoryFundTreatmentCatalog`

A catalog rejects treatment records belonging to another fund. This prevents accidentally applying one provider's treatment metadata to the other provider.

## Evidence and activation

Real provider execution remains fail-closed through `FailClosedStatutoryFundAdapter`.

Activation requires the existing official-adapter evidence and authorization machinery, plus authoritative provider contracts and staging/pilot evidence. No rate, percentage, threshold or formula is introduced by this module.

## Six-layer feasibility architecture

The repository was searched for an explicit six-layer architecture from the cited feasibility study and no matching design was found. Morva therefore does not invent those layers in code. When the authoritative study is supplied, the existing provider-neutral ports can be mapped to it without changing the legal treatment boundary.
