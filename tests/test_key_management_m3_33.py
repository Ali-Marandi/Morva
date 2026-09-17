import base64

import pytest

from morva.runtime.key_management import (
    InvalidKeyMaterialError,
    ManagedKeyRing,
    UnknownKeyVersionError,
)


def _key(byte: int, length: int = 32) -> str:
    return base64.urlsafe_b64encode(bytes([byte]) * length).decode().rstrip("=")


def test_encrypt_and_decrypt_bind_key_version_and_aad() -> None:
    ring = ManagedKeyRing.from_environment(
        active_version="v2",
        encryption_keys=f"v1:{_key(1)},v2:{_key(2)}",
        lookup_hmac_keys=f"v1:{_key(11)},v2:{_key(22)}",
    )

    token = ring.encrypt(b"4111111111111111", associated_data=b"employee.bank_account")

    assert token.startswith("v2.")
    assert ring.decrypt(token, associated_data=b"employee.bank_account") == b"4111111111111111"
    with pytest.raises(Exception):
        ring.decrypt(token, associated_data=b"employee.national_id")


def test_rotation_keeps_old_version_decryptable() -> None:
    old_ring = ManagedKeyRing.from_environment(
        active_version="v1",
        encryption_keys=f"v1:{_key(1)}",
        lookup_hmac_keys=f"v1:{_key(11)}",
    )
    token = old_ring.encrypt(b"sensitive-value")

    rotated_ring = ManagedKeyRing.from_environment(
        active_version="v2",
        encryption_keys=f"v1:{_key(1)},v2:{_key(2)}",
        lookup_hmac_keys=f"v1:{_key(11)},v2:{_key(22)}",
    )

    assert rotated_ring.decrypt(token) == b"sensitive-value"
    assert rotated_ring.encrypt(b"new-value").startswith("v2.")


def test_missing_retired_key_fails_closed() -> None:
    ring = ManagedKeyRing.from_environment(
        active_version="v2",
        encryption_keys=f"v2:{_key(2)}",
        lookup_hmac_keys=f"v2:{_key(22)}",
    )
    old_token = "v1.AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

    with pytest.raises(UnknownKeyVersionError):
        ring.decrypt(old_token)


def test_lookup_hmac_is_deterministic_and_context_bound() -> None:
    ring = ManagedKeyRing.from_environment(
        active_version="v1",
        encryption_keys=f"v1:{_key(1)}",
        lookup_hmac_keys=f"v1:{_key(11)}",
    )

    first = ring.lookup_hmac("0012345678", context="national_id")
    second = ring.lookup_hmac("0012345678", context="national_id")

    assert first == second
    assert first != ring.lookup_hmac("0012345678", context="bank_account")
    assert len(first) == 64


def test_key_ring_requires_matching_versions_and_strong_material() -> None:
    with pytest.raises(InvalidKeyMaterialError):
        ManagedKeyRing.from_environment(
            active_version="v1",
            encryption_keys=f"v1:{_key(1)}",
            lookup_hmac_keys=f"v2:{_key(22)}",
        )

    with pytest.raises(InvalidKeyMaterialError):
        ManagedKeyRing.from_environment(
            active_version="v1",
            encryption_keys=f"v1:{_key(1, 16)}",
            lookup_hmac_keys=f"v1:{_key(11)}",
        )
