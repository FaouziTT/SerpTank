from __future__ import annotations

import base64
import secrets

import pytest

from serptank.core.crypto import (
    DecryptionError,
    Keyring,
    constant_time_equals,
    generate_token,
    hash_token,
)


def _key() -> bytes:
    return secrets.token_bytes(32)


def test_roundtrip_and_ciphertext_is_randomised() -> None:
    ring = Keyring({"k1": _key()}, "k1")
    a = ring.encrypt("refresh-token", associated_data=b"conn:1")
    b = ring.encrypt("refresh-token", associated_data=b"conn:1")
    assert a != b
    assert ring.decrypt(a, associated_data=b"conn:1") == "refresh-token"
    assert "refresh-token" not in a


def test_associated_data_binds_context() -> None:
    ring = Keyring({"k1": _key()}, "k1")
    token = ring.encrypt("secret", associated_data=b"conn:1")
    with pytest.raises(DecryptionError):
        ring.decrypt(token, associated_data=b"conn:2")


def test_tampering_is_detected() -> None:
    ring = Keyring({"k1": _key()}, "k1")
    version, kid, nonce, ct = ring.encrypt("secret", associated_data=b"x").split(".")
    raw = bytearray(base64.urlsafe_b64decode(ct + "=" * (-len(ct) % 4)))
    raw[0] ^= 1
    tampered = ".".join(
        (version, kid, nonce, base64.urlsafe_b64encode(bytes(raw)).rstrip(b"=").decode())
    )
    with pytest.raises(DecryptionError):
        ring.decrypt(tampered, associated_data=b"x")


def test_rotation_keeps_old_ciphertexts_readable() -> None:
    old, new = _key(), _key()
    old_ring = Keyring({"k1": old}, "k1")
    token = old_ring.encrypt("v", associated_data=b"a")
    rotated = Keyring({"k1": old, "k2": new}, "k2")
    assert rotated.decrypt(token, associated_data=b"a") == "v"
    assert rotated.needs_rotation(token)
    assert not rotated.needs_rotation(rotated.encrypt("v", associated_data=b"a"))


@pytest.mark.parametrize("bad", ["", "v1.k1", "v2.k1.aa.bb", "v1.unknown.aa.bb", "a.b.c.d.e"])
def test_malformed_ciphertexts(bad: str) -> None:
    ring = Keyring({"k1": _key()}, "k1")
    with pytest.raises(DecryptionError):
        ring.decrypt(bad, associated_data=b"")


def test_keyring_validation() -> None:
    with pytest.raises(ValueError, match="active key"):
        Keyring({"k1": _key()}, "k2")
    with pytest.raises(ValueError, match="32 bytes"):
        Keyring({"k1": b"short"}, "k1")


def test_token_hashing() -> None:
    token = generate_token()
    assert len(token) >= 43
    digest = hash_token(token, pepper="pepper")
    assert digest == hash_token(token, pepper="pepper")
    assert digest != hash_token(token, pepper="other")
    assert constant_time_equals(digest, hash_token(token, pepper="pepper"))
