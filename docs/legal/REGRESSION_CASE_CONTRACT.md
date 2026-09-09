# Legal Component Regression Case Contract

Regression cases for legal payroll components prove calculation behavior without inventing statutory values.

Required governance targets for the current 1405 matrix:

- TAX
- PENSION
- INSURANCE
- LOAN
- COURT_ORDER

Each eventual authoritative case must identify the component and rule-pack version, provide a stable input fingerprint, state the approved treatment and classification flags, and carry a stable expected-output fingerprint.

A case is not production authority by itself. Activation still requires the approved legal source, rule evidence, calculation-matrix entry, reviewer/approver separation, timestamps, and matching regression-suite hash.

Cases must be deterministic and must not embed unverified tax rates, exemption thresholds, contribution percentages, or population-specific legal conclusions. Until authoritative evidence is entered, the contract verifies target coverage and fail-closed behavior only.
