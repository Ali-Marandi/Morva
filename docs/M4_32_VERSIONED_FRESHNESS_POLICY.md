# M4.32 Versioned Freshness Policy Identity

M4.32 makes the M4.29/M4.30 freshness-policy contract fully version-aware.

## Contract

- policy versions are positive integers;
- the policy fingerprint includes the explicit version;
- the same policy ID may retain multiple immutable versions;
- persistence preserves the supplied version rather than collapsing it to version 1;
- existing callers remain compatible because version 1 remains the default.

## API

Policy creation accepts `policy_version` with default `1`.

Registry-bound evaluation and direct policy lookup accept `policy_version` so callers can select an exact persisted identity.

The legacy caller-supplied-window endpoint also accepts the version parameter while retaining its original explicit `max_age_seconds` behavior.

## Safety boundary

This remains readiness/governance metadata only. No provider execution, credential use, payroll calculation, payment mutation or production authorization is introduced.
