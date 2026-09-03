"""verification.hasher — SHA-256 fingerprinting."""

from __future__ import annotations

import hashlib
from typing import Any

from .canonicalizer import canonicalize


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def hash_canonical(data: dict[str, Any]) -> str:
    """Hash canonical JSON of data → hex string (64 chars)."""
    return sha256_hex(canonicalize(data))


def hash_canonical_bytes(data: dict[str, Any]) -> bytes:
    """Hash canonical JSON → 32 bytes (for on-chain bytes32)."""
    return sha256_bytes(canonicalize(data))


def to_bytes32(hex_str: str) -> bytes:
    """Convert 64-char hex to 32 bytes."""
    h = hex_str.strip().lower().removeprefix("0x")
    if len(h) != 64:
        raise ValueError(f"Expected 64 hex chars, got {len(h)}: {hex_str[:32]}...")
    return bytes.fromhex(h)
