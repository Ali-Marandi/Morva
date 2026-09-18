# M3.45 Trusted Signing Key Registry

## Scope

M3.45 adds a versioned trust registry for Ed25519 release-signing keys.

Each registry entry contains:

- `key_id`: SHA-256 of the raw Ed25519 public-key bytes
- `public_key_sha256`: SHA-256 of the canonical DER SubjectPublicKeyInfo representation
- status: `active`, `retired`, or `revoked`
- timezone-aware validity start/end
- optional replacement key identifier

The registry itself has a monotonically increasing version and deterministic fingerprint.

## Trust decisions

A key is accepted only when:

1. it is explicitly registered
2. the supplied public key produces the registered `key_id`
3. the supplied public key matches the registered DER fingerprint
4. its status is `active`
5. the verification time is within its configured validity window

Unknown, retired, revoked and expired keys are rejected.

## Rotation and revocation

`rotate_key` creates a new registry version, retires the previous active key and records the
replacement relationship. `revoke_key` creates a new registry version with the target key
marked revoked.

The registry is immutable by construction: operations return a new registry value rather than
mutating the existing record.

## Production boundary

No private signing key is stored in the registry or repository. Production signing-key custody,
KMS/HSM controls, operator authorization, emergency revocation and audited registry publication
remain operational requirements outside this code contract.
