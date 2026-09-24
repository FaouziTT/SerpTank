"""Cryptographic primitives: field encryption keyring and token hashing.

Field encryption (OWASP A04:2025)
---------------------------------
Secrets we must be able to read back (OAuth refresh tokens, TOTP seeds, webhook secrets,
provider API keys) are encrypted with AES-256-GCM. Ciphertexts are self-describing::

    v1.<key_id>.<base64url(nonce)>.<base64url(ciphertext+tag)>

so keys can be rotated: new writes use the *active* key, and old records remain
readable as long as their key stays in the keyring. ``associated_data`` binds a
ciphertext to its context (e.g. ``b"connection:<uuid>:refresh_token"``) so a value
copied into another row or column fails to decrypt.

Token hashing
-------------
Values we only ever need to *compare* (session ids, reset tokens, API-key secrets,
recovery codes) are never stored in plaintext. They are stored as HMAC-SHA256 digests
keyed with a server-side pepper, and compared in constant time.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_VERSION = "v1"
_NONCE_BYTES = 12


class DecryptionError(Exception):
    """Raised when a ciphertext is malformed, uses an unknown key, or fails authentication."""


def _b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64d(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


@dataclass(frozen=True)
class Keyring:
    """A set of AES-256 keys with one active key used for new encryptions."""

    keys: dict[str, bytes]
    active_key_id: str

    def __post_init__(self) -> None:
        if self.active_key_id not in self.keys:
            msg = "active key id is not in the keyring"
            raise ValueError(msg)
        for key_id, key in self.keys.items():
            if len(key) != 32 or "." in key_id:  # noqa: PLR2004
                msg = f"key {key_id!r} must be 32 bytes and its id must not contain '.'"
                raise ValueError(msg)

    def encrypt(self, plaintext: str, *, associated_data: bytes) -> str:
        nonce = secrets.token_bytes(_NONCE_BYTES)
        aead = AESGCM(self.keys[self.active_key_id])
        ciphertext = aead.encrypt(nonce, plaintext.encode("utf-8"), associated_data)
        return ".".join((_VERSION, self.active_key_id, _b64e(nonce), _b64e(ciphertext)))

    def decrypt(self, token: str, *, associated_data: bytes) -> str:
        try:
            version, key_id, nonce_b64, ct_b64 = token.split(".")
        except ValueError as exc:
            raise DecryptionError("malformed ciphertext") from exc
        if version != _VERSION or key_id not in self.keys:
            raise DecryptionError("unsupported version or unknown key")
        try:
            aead = AESGCM(self.keys[key_id])
            plaintext = aead.decrypt(_b64d(nonce_b64), _b64d(ct_b64), associated_data)
        except (InvalidTag, ValueError) as exc:
            raise DecryptionError("ciphertext failed authentication") from exc
        return plaintext.decode("utf-8")

    def needs_rotation(self, token: str) -> bool:
        """True when ``token`` was encrypted with a non-active key (re-encrypt it)."""
        parts = token.split(".")
        return len(parts) != 4 or parts[1] != self.active_key_id  # noqa: PLR2004

    @staticmethod
    def generate_key() -> str:
        """Return a new base64url-encoded 32-byte key for the keyring config."""
        return _b64e(secrets.token_bytes(32))


def generate_token(nbytes: int = 32) -> str:
    """Cryptographically secure URL-safe random token (default 256 bits)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str, *, pepper: str) -> str:
    """Keyed hash of a secret token for storage/lookup (HMAC-SHA256, hex)."""
    return hmac.new(pepper.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
