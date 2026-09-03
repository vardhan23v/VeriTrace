"""face.matcher — cosine-similarity matching."""

from __future__ import annotations

import numpy as np

from .detector import DetectedFace


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity for L2-normalised embeddings. Returns [-1, 1]."""
    if a.shape != b.shape:
        # If dims mismatch (e.g. fallback 512 vs real 512) pad shorter — already padded to 512
        # but handle generically
        max_len = max(a.shape[0], b.shape[0])
        ap = np.zeros(max_len, dtype=np.float32)
        bp = np.zeros(max_len, dtype=np.float32)
        ap[: a.shape[0]] = a
        bp[: b.shape[0]] = b
        a, b = ap, bp
    # Embeddings are L2-normalised so dot == cosine
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom < 1e-9:
        return 0.0
    return float(np.dot(a, b) / denom)


def is_match(similarity: float, threshold: float = 0.60) -> bool:
    """True if similarity meets face-match threshold."""
    return similarity >= threshold


def best_match(
    query_emb: np.ndarray,
    candidates: list[tuple[DetectedFace, dict]],
    threshold: float = 0.60,
) -> tuple[DetectedFace, dict, float] | None:
    """Given query embedding and list of (face, meta), return best match above threshold.

    candidates: list of (DetectedFace, metadata_dict)
    Returns (face, meta, score) or None.
    """
    best: tuple[DetectedFace, dict, float] | None = None
    best_score = -1.0
    for face, meta in candidates:
        score = cosine_similarity(query_emb, face.embedding)
        if score > best_score:
            best_score = score
            best = (face, meta, score)
    if best is not None and best_score >= threshold:
        return best
    return None


def rank_candidates(
    query_emb: np.ndarray,
    candidates: list[tuple[DetectedFace, dict]],
) -> list[tuple[DetectedFace, dict, float]]:
    """Return all candidates ranked descending by similarity."""
    scored = [(face, meta, cosine_similarity(query_emb, face.embedding)) for face, meta in candidates]
    scored.sort(key=lambda x: x[2], reverse=True)
    return scored
