import base64
import hashlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from morva.security.field_crypto import decrypt, encrypt


def test_hkdf_v2_round_trip_uses_versioned_ciphertext() -> None:
    token = encrypt(
        "secret",
        key_material="managed-high-entropy-secret",
        key_version="2",
    )
    assert token.startswith("v2.")
    assert decrypt(token, key_material="managed-high-entropy-secret") == "secret"


def test_legacy_v1_ciphertext_remains_decryptable() -> None:
    material = "legacy-managed-secret"
    key = hashlib.sha256(material.encode("utf-8")).digest()
    nonce = b"0123456789ab"
    ciphertext = AESGCM(key).encrypt(nonce, b"old-value", None)
    token = base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")

    assert decrypt(token, key_material=material) == "old-value"


def test_explicit_key_version_round_trip() -> None:
    first = encrypt("same", key_material="managed-high-entropy-secret", key_version="7")
    second = encrypt("same", key_material="managed-high-entropy-secret", key_version="7")
    assert first != second
    assert (
        decrypt(
            first,
            key_material="managed-high-entropy-secret",
            key_version="7",
        )
        == "same"
    )
    assert (
        decrypt(
            second,
            key_material="managed-high-entropy-secret",
            key_version="7",
        )
        == "same"
    )
