# M4.5 — Rule-Pack Evidence Bridge

M4.5 binds an existing 1405 `RuleComponentEvidence` record to a corresponding M4.1 `legal_rule` evidence item.

## Contract

The bridge requires:
- a supported 1405 component;
- exact authoritative evidence ID binding;
- exact source URI, issuer and SHA-256 identity;
- exact employee-population scope at binding time;
- explicit treatment and tax/pension/insurance classification;
- distinct reviewer/approver identities;
- an evidence record that remains `review_required` until formal activation.

The binding fails closed if legal evidence is missing, unaccepted, future-dated, expired, out of scope or hash-inconsistent.

## Safety

No statutory numeric rate, threshold, exemption amount, ministry dataset, employee record, credential, provider endpoint or production activation is introduced.
