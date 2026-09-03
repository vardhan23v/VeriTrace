"""tests/test_canonicalization.py — key-order independence."""

import json


def test_key_order_independence():
    from src.verification.canonicalizer import canonicalize, build_canonical_record
    from src.verification.hasher import hash_canonical

    # Same logical data, different insertion order
    d1 = {"platform": "instagram.com", "post_url": "https://example.com/p/1", "title": "Hello", "caption": "World", "image_sha256": "abc123", "author": "alice", "published_at": "2024-01-01T00:00:00Z", "image_url": "https://cdn.example.com/a.jpg"}
    d2 = {"image_url": "https://cdn.example.com/a.jpg", "author": "alice", "caption": "World", "title": "Hello", "post_url": "https://example.com/p/1", "platform": "instagram.com", "published_at": "2024-01-01T00:00:00Z", "image_sha256": "abc123"}

    assert canonicalize(d1) == canonicalize(d2)
    assert hash_canonical(d1) == hash_canonical(d2)


def test_nested_sort():
    from src.verification.canonicalizer import canonicalize

    a = {"z": 1, "a": {"y": 2, "x": 1}}
    b = {"a": {"x": 1, "y": 2}, "z": 1}
    assert canonicalize(a) == canonicalize(b)


def test_utf8_stable():
    from src.verification.canonicalizer import canonicalize

    d = {"title": "café — naïve", "caption": "emoji 😀"}
    b = canonicalize(d)
    # should be valid utf-8 and round-trip
    assert b.decode("utf-8") == json.dumps(d, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def test_build_canonical_schema():
    from src.verification.canonicalizer import build_canonical_record

    rec = build_canonical_record(platform="x.com", post_url="https://x.com/1", title="t", caption="c", image_sha256="deadbeef", author="bob", published_at="2024-02-02", image_url="https://cdn/img.jpg")
    # All expected keys present and strings
    for k in ["platform", "post_url", "title", "caption", "image_sha256", "author", "published_at", "image_url"]:
        assert k in rec
        assert isinstance(rec[k], str)
