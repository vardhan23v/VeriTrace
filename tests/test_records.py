"""tests/test_records.py — record helpers: tamper copy, listing, resolve, verify_pipeline (local + on-chain)."""

import json

import pytest


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    from src.config import Config

    monkeypatch.setattr(Config, "DATA_DIR", tmp_path)
    return tmp_path


def _write_record(data_dir, rid="abc12345", **overrides):
    from src.config import Config
    from src.verification.canonicalizer import build_canonical_record
    from src.verification.hasher import hash_canonical

    canonical = build_canonical_record(
        platform="Wikipedia",
        post_url="https://en.wikipedia.org/wiki/X",
        title="X",
        caption="orig caption",
        image_sha256="ab" * 32,
        image_url="https://img/x.jpg",
    )
    h = hash_canonical(canonical)
    rec = {
        "record_id": rid,
        "canonical": canonical,
        "data_hash": "0x" + h,
        "data_hash_hex": h,
        "best_match": {"platform": "Wikipedia", "post_url": canonical["post_url"], "similarity": 0.9},
        "blockchain": {"contract_address": ""},
        **overrides,
    }
    p = Config.records_dir() / f"{rid}.json"
    p.write_text(json.dumps(rec))
    (Config.data_dir() / "latest_record.json").write_text(json.dumps(rec))
    return rec, p


def test_tamper_record_changes_hash_and_marks_origin(data_dir):
    from src.pipeline import tamper_record
    from src.verification.hasher import hash_canonical

    rec, _ = _write_record(data_dir)
    dst = tamper_record("abc12345")
    t = json.loads(dst.read_text())
    assert t["record_id"] == "abc12345-tampered"
    assert t["tampered_from"] == "abc12345"
    assert t["canonical"]["caption"] != rec["canonical"]["caption"]
    assert hash_canonical(t["canonical"]) != rec["data_hash_hex"]


def test_tamper_unknown_field_raises(data_dir):
    from src.pipeline import tamper_record

    _write_record(data_dir)
    with pytest.raises(ValueError, match="not in canonical"):
        tamper_record("latest", field="nope")


def test_list_and_resolve(data_dir):
    from src.pipeline import list_records, resolve_record_path

    _write_record(data_dir)
    assert [r["record_id"] for r in list_records()] == ["abc12345"]
    assert resolve_record_path("latest").name == "latest_record.json"
    assert resolve_record_path("abc12345").name == "abc12345.json"
    with pytest.raises(FileNotFoundError):
        resolve_record_path("missing")


def test_verify_pipeline_local_mode_detects_tamper(data_dir):
    """No contract on chain → local hash comparison still separates VERIFIED from TAMPERED."""
    from src.blockchain.client import get_web3
    from src.pipeline import tamper_record, verify_pipeline

    _write_record(data_dir)
    w3 = get_web3(rpc_url="http://127.0.0.1:1")
    ok = verify_pipeline("abc12345", w3=w3, verbose=False)
    assert ok["mode"] == "local-only" and ok["verified"] and ok["status"] == "VERIFIED"
    tamper_record("abc12345")
    bad = verify_pipeline("abc12345-tampered", w3=w3, verbose=False)
    assert bad["status"] == "TAMPERED" and not bad["hashes_match"]


def test_verify_pipeline_on_chain(data_dir):
    """Store the hash on a real (in-memory) chain, then verify original vs tampered against it."""
    from src.blockchain.client import VerificationRegistryClient, get_web3
    from src.pipeline import tamper_record, verify_pipeline

    rec, p = _write_record(data_dir)
    w3 = get_web3(rpc_url="http://127.0.0.1:1")
    client = VerificationRegistryClient(w3)
    addr = client.ensure_deployed()
    receipt = client.store(rec["data_hash_hex"])
    rec["blockchain"] = {"contract_address": addr, "tx_hash": receipt["tx_hash"]}
    p.write_text(json.dumps(rec))

    ok = verify_pipeline("abc12345", w3=w3, verbose=False)
    assert ok["mode"] == "on-chain" and ok["verified"]
    assert ok["event"]["tx_hash"] == receipt["tx_hash"]

    tamper_record("abc12345")
    bad = verify_pipeline("abc12345-tampered", w3=w3, verbose=False)
    assert bad["status"] == "TAMPERED"
    assert bad["current_hash_on_chain"] is False and bad["recorded_hash_on_chain"] is True


def test_phash_similarity_tracks_visual_edits(tmp_path):
    import cv2
    import numpy as np

    from src.verification.phash import hamming, phash, similarity

    rng = np.random.default_rng(0)
    img = rng.integers(0, 255, (128, 128, 3), dtype=np.uint8)
    img = cv2.GaussianBlur(img, (15, 15), 0)
    a = tmp_path / "a.png"
    cv2.imwrite(str(a), img)
    # re-encode as JPEG (byte-level change, visually the same)
    b = tmp_path / "b.jpg"
    cv2.imwrite(str(b), img, [cv2.IMWRITE_JPEG_QUALITY, 60])
    # heavy edit
    c = tmp_path / "c.png"
    cv2.imwrite(str(c), 255 - cv2.flip(img, 0))
    ha, hb, hc = phash(a), phash(b), phash(c)
    assert len(ha) == 16
    assert a.read_bytes() != b.read_bytes()
    assert hamming(ha, hb) <= 6
    assert similarity(ha, hb) > similarity(ha, hc)
