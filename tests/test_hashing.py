"""tests/test_hashing.py — deterministic hashing."""

import hashlib
import json


def test_same_data_same_hash():
    from src.verification.hasher import hash_canonical

    data = {"platform": "instagram.com", "post_url": "https://example.com/p/1", "title": "hello"}
    # pad to full schema for stability but same principle
    from src.verification.canonicalizer import build_canonical_record

    rec1 = build_canonical_record(platform="instagram.com", post_url="https://example.com/p/1", title="hello", caption="hi", image_sha256="abc", author="alice", published_at="2024-01-01", image_url="https://cdn.example.com/a.jpg")
    rec2 = build_canonical_record(platform="instagram.com", post_url="https://example.com/p/1", title="hello", caption="hi", image_sha256="abc", author="alice", published_at="2024-01-01", image_url="https://cdn.example.com/a.jpg")
    assert hash_canonical(rec1) == hash_canonical(rec2)


def test_changed_data_different_hash():
    from src.verification.hasher import hash_canonical
    from src.verification.canonicalizer import build_canonical_record

    base = dict(platform="instagram.com", post_url="https://example.com/p/1", title="hello", caption="hi", image_sha256="abc", author="alice", published_at="2024-01-01", image_url="https://cdn.example.com/a.jpg")
    rec1 = build_canonical_record(**base)
    rec2 = build_canonical_record(**{**base, "caption": "modified"})
    assert hash_canonical(rec1) != hash_canonical(rec2)


def test_hash_is_64_hex():
    from src.verification.hasher import hash_canonical
    from src.verification.canonicalizer import build_canonical_record

    rec = build_canonical_record(platform="x", post_url="https://example.com", title="t", caption="c", image_sha256="deadbeef")
    h = hash_canonical(rec)
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
