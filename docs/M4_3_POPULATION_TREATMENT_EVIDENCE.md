# M4.3 — Population-Scoped Treatment Evidence

M4.3 adds a software boundary for binding an approved legal-source evidence item to the treatment of a payroll component for an exact employee population.

## Contract

Each treatment record requires:
- a 1405 component code;
- an exact population scope;
- an M4.1 authoritative evidence ID;
- explicit earning/deduction treatment and boolean tax/pension/insurance flags;
- distinct reviewer and approver identities with timezone-aware timestamps.

Activation remains fail-closed until the bound authority evidence is accepted, effective, approved and unexpired for the same population. A complete 1405 treatment set may be evaluated without containing any statutory numeric rates.

## Safety

No statutory rate, threshold, exemption amount, ministry dataset, employee record, credential, provider endpoint or production payment behavior is introduced.
