# M3.37 — Formal release certification evidence

## Scope

M3.37 adds a software-enforced release certification contract. It is a governance and evidence boundary; it does not manufacture, simulate or infer human approval.

## Required certification evidence

A release candidate must bind to an exact Git commit SHA and identify every required evidence artifact. The current baseline domains are:

- independent security assessment
- disaster-recovery / RTO-RPO evidence
- target-scale load and performance evidence
- three-way reconciliation evidence

Each evidence identifier must be explicit and unique.

## Formal signoff

The release contract requires distinct, timezone-aware signoffs from finance, legal and operations. Duplicate signatures for the same role are rejected.

## Fail-closed release rule

Release readiness remains false until all required evidence is verified, all three formal signoffs exist, and the security, disaster-recovery, load/performance and reconciliation signoff domains are complete.

`ReleaseCertification.fingerprint` creates a deterministic SHA-256 binding over the release candidate, evidence identifiers, domain gates and signoff provenance.

## What remains external

This contract does not constitute the independent security assessment itself, a production DR drill, a production-scale performance certification, or live three-way settlement evidence. Those artifacts must be produced and approved by the responsible independent or operational authorities before a production release can pass the contract.
