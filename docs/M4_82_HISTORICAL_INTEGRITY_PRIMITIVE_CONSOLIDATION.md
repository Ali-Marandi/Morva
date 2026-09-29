# M4.82 — Historical Integrity Primitive Consolidation

## Purpose

M4.82 reduces repeated integrity primitives introduced during the M4.69–M4.81 chain by centralizing canonical UTC timestamps and canonical SHA-256 JSON serialization.

## Shared primitives

`src/morva/runtime/historical_integrity_primitives.py` provides deterministic timezone normalization and key-order-independent SHA-256 hashing. Newer M4.77/M4.78 runtime layers use these primitives for history and aggregate fingerprints.

The consolidation preserves the existing fingerprint schema and verification semantics; it does not alter persistence or production authority boundaries.
