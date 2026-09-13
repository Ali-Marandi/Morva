# M3.20 — Authoritative Master Data Acceptance & Drift

## Objective

M3.20 turns the existing master-data acceptance boundary into an explicit, repeatable evidence contract. An accepted dataset is usable only while the persisted population, integrity snapshot and acceptance fingerprint remain unchanged.

## Acceptance contract

A dataset assessment records:

- dataset identity and schema version;
- source system and authoritative source reference;
- evidence reference and SHA-256;
- population scope and coverage counts;
- dataset period and SHA-256;
- row, duplicate and rejected-row counts;
- schema validation result;
- persisted master-data integrity snapshot hash;
- deterministic evidence fingerprint;
- distinct submission and authority confirmation evidence.

Assessment is eligible only when the contract, current integrity gate and persisted coverage all pass. Confirmation requires a distinct authority and rechecks the live state before changing the record to `accepted`.

## Drift contract

`detect_master_data_drift()` compares an accepted assessment against the current database state and reports:

1. acceptance status/authority evidence problems;
2. current master-data integrity blockers;
3. integrity snapshot hash drift;
4. per-entity population-count deltas;
5. acceptance evidence fingerprint inconsistency.

Any detected drift is blocking for production readiness. The detector does not silently repair, overwrite or re-accept data.

## Safety boundary

M3.20 does not invent ministry data, legal rules, population definitions or organizational authority. It provides the software evidence boundary required to consume those authoritative artifacts once supplied and formally accepted.

Real employee data and authoritative source artifacts must remain outside Git and enter through the approved import/provenance path.
