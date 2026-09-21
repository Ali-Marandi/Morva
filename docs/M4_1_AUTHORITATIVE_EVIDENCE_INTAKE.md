# M4.1 — Authoritative Evidence Intake

M4.1 establishes a reusable, fail-closed software boundary for admitting authoritative external evidence without inventing or activating external data.

## Contract

Each evidence item records:

- a stable evidence identifier and source type;
- the authoritative source URI and SHA-256 digest supplied by the real source owner;
- issuer and exact population scope;
- effective validity window;
- pending/accepted/rejected status;
- approval actor and approval timestamp when accepted;
- optional evidence expiry;
- deterministic item and registry fingerprints.

The registry sorts evidence deterministically, rejects duplicate identifiers, is write-once, and exposes an explicit activation-readiness check. Activation is **not** proof that the underlying authority exists; it is only true when real evidence has been recorded as accepted and has not expired.

## Safety boundary

M4.1 does not add ministry datasets, employee records, statutory rates, credentials, external mutations or production payment behavior. Real evidence must be supplied through the authoritative intake process and independently approved before activation.

## Next evidence-closure inputs

The contract is intentionally provider-neutral. The next inputs are real, separately controlled artifacts for authoritative master data, 1405 legal rules, population-specific treatments, official adapter contracts, staging/pilot execution, reconciliation, disaster recovery and independent security evidence.
