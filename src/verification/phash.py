"""verification.phash — perceptual hash (DCT pHash) for near-duplicate image detection.

SHA-256 flips completely when a single byte changes; pHash changes *proportionally*
to visual edits. Storing both lets the verifier say not just "tampered" but
"tampered, and the image is ~93% visually similar to the original" — useful for
telling a re-encoded copy from a manipulated one. pHash is informational only;
the on-chain fingerprint stays SHA-256 of the canonical record.
"""

from __future__ import annotations

import os

import cv2
import numpy as np


def phash(image_path: str | os.PathLike, hash_size: int = 8, highfreq_factor: int = 4) -> str:
    """Return a 64-bit perceptual hash as 16 hex chars. Raises ValueError if unreadable."""
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Unable to read image for pHash: {image_path}")
    size = hash_size * highfreq_factor
    resized = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32)
    dct = cv2.dct(resized)
    low = dct[:hash_size, :hash_size]
    med = np.median(low)
    bits = (low > med).flatten()
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return f"{value:0{hash_size * hash_size // 4}x}"


def hamming(a: str, b: str) -> int:
    """Hamming distance between two hex pHashes (number of differing bits)."""
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def similarity(a: str, b: str, bits: int = 64) -> float:
    """1.0 = identical, 0.0 = every bit differs."""
    return 1.0 - hamming(a, b) / bits
