"""Text fingerprints: exact duplicates (SHA-256) and near duplicates (64-bit SimHash)."""

from __future__ import annotations

import hashlib
import re

_WORD = re.compile(r"\w+", re.UNICODE)
SIMHASH_BITS = 64


def words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def content_hash(tokens: list[str]) -> str:
    return hashlib.sha256(" ".join(tokens).encode()).hexdigest()


def simhash(tokens: list[str], shingle: int = 3) -> int:
    """Charikar SimHash over word shingles; similar texts differ in few bits."""
    if not tokens:
        return 0
    weights = [0] * SIMHASH_BITS
    grams = (
        [" ".join(tokens[i : i + shingle]) for i in range(len(tokens) - shingle + 1)]
        if len(tokens) >= shingle
        else [" ".join(tokens)]
    )
    for gram in grams:
        digest = int.from_bytes(hashlib.blake2b(gram.encode(), digest_size=8).digest(), "big")
        for bit in range(SIMHASH_BITS):
            weights[bit] += 1 if digest >> bit & 1 else -1
    value = 0
    for bit, weight in enumerate(weights):
        if weight > 0:
            value |= 1 << bit
    return value


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def to_signed(value: int) -> int:
    """Store an unsigned 64-bit hash in a signed BIGINT column."""
    return value - (1 << 64) if value >= 1 << 63 else value


def from_signed(value: int) -> int:
    return value + (1 << 64) if value < 0 else value
