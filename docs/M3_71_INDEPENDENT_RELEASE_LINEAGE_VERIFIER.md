# M3.71 — Independent Production Release Lineage Verifier

M3.71 independently reconstructs the M3.70 lineage manifest from the underlying technical
readiness gate, final-readiness receipt, production-certification receipt, external evidence
registry and full production-boundary policy receipt.

The verifier compares the stored lineage object byte-for-byte at the semantic object level
with the independently rebuilt object and writes only a write-once verification receipt.

It performs no release, certification, promotion or deployment mutation.
