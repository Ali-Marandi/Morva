# M4.8 — Three-Way Reconciliation Evidence

M4.8 binds the three reconciliation artifacts:
Morva entitlement ↔ Treasury/PFM instruction ↔ Bank settlement.

The contract keeps two distinct integrity layers:
- independent SHA-256 identities for each of the three artifacts;
- a separate SHA-256 for the authoritative reconciliation-evidence document;
- a comparison fingerprint describing the comparison result.

Activation requires accepted M4.1 `reconciliation` evidence whose authoritative source digest matches the reconciliation-evidence document digest and whose approval/effective window is current.

No payment execution or live provider call is performed, and no real financial or employee data is stored in Git.
