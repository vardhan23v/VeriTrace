"""verification.canonicalizer — deterministic JSON canonicalization for hashing."""

from __future__ import annotations

import json
from typing import Any


def canonicalize(data: dict[str, Any]) -> bytes:
    """Deterministic serialization:
    - sorted keys (recursive via json.dumps sort_keys)
    - UTF-8
    - no whitespace (separators=(',',':'))
    - ensure_ascii=False so UTF-8 is preserved
    Returns UTF-8 bytes ready for hashing.
    """
    # json.dumps with sort_keys handles nested dicts recursively
    text = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return text.encode("utf-8")


def canonical_json(data: dict[str, Any]) -> str:
    """Human-readable canonical JSON (sorted, compact)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ── Schema for discovered post ────────────────────────────────


def build_canonical_record(
    *,
    platform: str,
    post_url: str,
    title: str,
    caption: str,
    image_sha256: str,
    author: str = "",
    published_at: str = "",
    image_url: str = "",
) -> dict[str, str]:
    """Build the canonical record dict that will be hashed.

    Exact schema (documented in README):
        {
          "platform": "...",
          "post_url": "...",
          "title": "...",
          "caption": "...",
          "image_sha256": "...",   # hex of candidate image bytes
          "author": "...",
          "published_at": "...",
          "image_url": "..."
        }
    All values are strings; missing fields are "" (not omitted) to keep hash stable.
    """
    return {
        "author": author or "",
        "caption": caption or "",
        "image_sha256": image_sha256 or "",
        "image_url": image_url or "",
        "platform": platform or "",
        "post_url": post_url or "",
        "published_at": published_at or "",
        "title": title or "",
    }
