# M3.48 Trusted-Key Rotation Ceremony

## Scope

M3.48 defines a deterministic, fail-closed evidence contract for rotating the release-signing
trust registry from version N to version N+1.

The ceremony records:

- a unique ceremony ID;
- the registry ID and consecutive source/target versions;
- the exact old and replacement signing-key IDs;
- the exact effective timestamp for the replacement key;
- the source and target registry fingerprints;
- the root trust-anchor key ID;
- a deterministic ceremony fingerprint.

## Verification contract

A valid ceremony requires all of the following:

1. Both source registries are signed and independently verified with the supplied root public key.
2. Both registries use the same root trust anchor.
3. The registry ID is unchanged and the version advances by exactly one.
4. The old key is active in the previous registry and retired in the new registry.
5. The retired key names exactly the replacement key.
6. The replacement key is absent from the previous registry and active in the new registry.
7. The replacement key valid_from equals the ceremony effective_at.
8. Every non-rotated key is unchanged at the registry-record level.
9. The ceremony fingerprints match the actual source registries and serialized ceremony payload.

The ceremony does not mutate either registry. It proves that two already-signed registry versions form
the declared rotation transition.

## Operational boundary

The M3.48 CI workflow uses ephemeral keys and rehearsal-only registries. It does not create or approve
production trust material.

Production use still requires controlled root-key custody, separation of duties, documented authorization,
key storage/backup policy, incident/revocation procedures, independent security validation, and formally
approved operational evidence.

## Failure behavior

Any mismatch in signatures, root key, versions, key states, replacement linkage, effective time,
registry fingerprints, or ceremony fingerprint causes verification to fail closed.
