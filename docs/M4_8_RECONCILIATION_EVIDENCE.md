# M4.8 — Three-Way Reconciliation Evidence

M4.8 binds the three artifacts required for end-to-end reconciliation:
`Morva entitlement ↔ Treasury/PFM instruction ↔ Bank settlement`.

Each evidence record carries independent SHA-256 identities for the three artifacts plus a comparison fingerprint and exact population/period scope.

Activation requires an accepted M4.1 `reconciliation` evidence item whose digest matches the comparison fingerprint and whose effective/approval window is current.

No payment execution or live provider call is performed, and no real financial or employee data is stored in Git.
