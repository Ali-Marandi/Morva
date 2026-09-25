# M4.24 Verified Readiness Persistence Boundary

M4.24 makes the persistence entry path explicit and fail-closed.

## Required chain

The only supported ingestion service is:

`assessment JSON file → M4.21 independent verifier → persisted verification record`

The service accepts:

- the assessment file path;
- the canonical repository identity;
- the exact candidate commit SHA;
- the verification timestamp.

It does **not** accept a caller-supplied verification fingerprint. M4.21 derives that fingerprint from the independently verified assessment fingerprint and verification time.

## Failure behavior

Persistence is not reached when:

- the assessment repository differs from the canonical repository;
- the assessment candidate SHA differs from the exact caller-supplied candidate SHA;
- the assessment fingerprint is invalid or tampered;
- the assessment structure is invalid;
- the verification timestamp precedes the assessment check time.

A blocked assessment is still a valid software-side receipt and remains blocked after persistence. This preserves the distinction between "verified receipt" and "ready for execution."

## Safety boundary

M4.24 performs no provider calls, credential use, payroll calculation, payment mutation, external evidence fabrication or production authorization. It is an internal persistence-boundary service for already-produced M4.20 assessment artifacts.
