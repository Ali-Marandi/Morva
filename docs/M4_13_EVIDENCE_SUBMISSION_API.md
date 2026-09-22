# M4.13 — Evidence Submission API

M4.13 turns authoritative evidence intake into a controlled API workflow.

## Flow

1. A principal with `evidence.submit` creates a submission.
2. The server stores it only as `pending` and computes a deterministic fingerprint.
3. A separate principal with `evidence.approve` may accept or reject it.
4. Every transition is appended to the immutable audit chain.
5. A decided record cannot be decided again.

## Safety boundary

The API stores metadata and SHA-256 identities. It does not upload, invent or activate authoritative evidence, does not bypass approval, and does not grant production certification.
