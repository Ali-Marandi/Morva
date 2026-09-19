# M3.63 — Evidence Freshness Gate

## Purpose

M3.63 rejects technically valid but stale release, approval or deployment evidence
before a prospective production promotion.

## Contract

The gate requires timezone-aware timestamps for:

- the published Release;
- the promotion approval;
- the deployment evidence;
- the evaluation time.

Each age window is explicit and included in the gate fingerprint. Future timestamps are
rejected.

## Safety boundary

M3.63 does not publish, promote or deploy anything. It creates only a time-bound,
write-once technical evidence gate.

The configured freshness windows are policy inputs; this milestone does not assert that a
particular window is legally or operationally sufficient for production.
