# M3.24 — 1405 Rule-Pack Primary-Source Evidence Boundary

## Objective

M3.24 connects the existing 1405 component matrix and primary-source register to a deterministic, machine-checkable evidence contract for every required payroll component.

## Contract

Each component evidence record must identify:

- the governed component code and registered `source_id`;
- a primary-source citation and issuer;
- an HTTPS locator and SHA-256 document hash;
- adoption and effective dates;
- timezone-aware retrieval time;
- distinct reviewer and approver identities;
- regression evidence reference;
- explicit earning/deduction treatment;
- explicit taxable, pensionable and insurable treatment.

The validator fingerprints the complete evidence set deterministically.

## Safety boundary

This tranche does **not** activate any 1405 legal amount, tax bracket, pension rate, insurance percentage, overtime coefficient or other statutory value. Evidence remains `review_required` until the actual primary artifact and formal approvals are supplied through the governed process.

Secondary reporting may help discover candidate sources, but it is not sufficient for production activation. Missing or unresolved primary evidence remains fail-closed.

## Current status

The repository now has the software control to reject incomplete, mismatched or non-provenanced component evidence. The actual authoritative 1405 artifacts and formal finance/legal approvals are still external prerequisites.
