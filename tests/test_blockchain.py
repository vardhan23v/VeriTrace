"""tests/test_blockchain.py — store / retrieve / tamper via eth-tester."""

import pytest


def test_store_and_verify():
    from src.blockchain.client import VerificationRegistryClient, get_web3
    from src.verification.canonicalizer import build_canonical_record
    from src.verification.hasher import hash_canonical

    w3 = get_web3()  # eth-tester
    client = VerificationRegistryClient(w3)
    addr = client.ensure_deployed()
    assert addr.startswith("0x")

    rec = build_canonical_record(
        platform="test.com",
        post_url="https://test.com/p/1",
        title="Hello",
        caption="World",
        image_sha256="abc123",
        author="alice",
        published_at="2024-01-01",
        image_url="https://cdn/test.jpg",
    )
    h = hash_canonical(rec)

    receipt = client.store(h)
    assert "tx_hash" in receipt
    assert receipt["block_number"] is not None

    exists, ts = client.verify(h)
    assert exists is True
    assert ts > 0


def test_tamper_detection():
    from src.blockchain.client import VerificationRegistryClient, get_web3
    from src.verification.canonicalizer import build_canonical_record
    from src.verification.hasher import hash_canonical

    w3 = get_web3()
    client = VerificationRegistryClient(w3)
    client.ensure_deployed()

    rec = build_canonical_record(
        platform="test.com",
        post_url="https://test.com/p/2",
        title="Original",
        caption="Caption",
        image_sha256="abc",
        author="bob",
        published_at="2024-01-02",
        image_url="https://cdn/2.jpg",
    )
    h_original = hash_canonical(rec)
    client.store(h_original)

    # tampered: change caption
    tampered = build_canonical_record(
        platform="test.com",
        post_url="https://test.com/p/2",
        title="Original",
        caption="TAMPERED",
        image_sha256="abc",
        author="bob",
        published_at="2024-01-02",
        image_url="https://cdn/2.jpg",
    )
    h_tampered = hash_canonical(tampered)

    assert h_original != h_tampered

    exists_tampered, _ = client.verify(h_tampered)
    assert exists_tampered is False  # tampered hash not stored

    exists_orig, _ = client.verify(h_original)
    assert exists_orig is True


def test_duplicate_rejected():
    from src.blockchain.client import VerificationRegistryClient, get_web3
    from src.verification.canonicalizer import build_canonical_record
    from src.verification.hasher import hash_canonical

    w3 = get_web3()
    client = VerificationRegistryClient(w3)
    client.ensure_deployed()

    rec = build_canonical_record(
        platform="dup.com",
        post_url="https://dup.com/1",
        title="Dup",
        caption="test",
        image_sha256="duphash",
        author="",
        published_at="",
        image_url="https://cdn/dup.jpg",
    )
    h = hash_canonical(rec)
    client.store(h)
    # second store should revert
    with pytest.raises(RuntimeError, match="reverted|already"):
        client.store(h)


def test_verify_nonexistent():
    from src.blockchain.client import VerificationRegistryClient, get_web3

    w3 = get_web3()
    client = VerificationRegistryClient(w3)
    client.ensure_deployed()
    fake = "ab" * 32
    exists, ts = client.verify(fake)
    assert exists is False
    assert ts == 0


def test_store_returns_0x_tx_hash_and_event_lookup():
    from src.blockchain.client import VerificationRegistryClient, get_web3
    from src.verification.canonicalizer import build_canonical_record
    from src.verification.hasher import hash_canonical

    w3 = get_web3()
    client = VerificationRegistryClient(w3)
    client.ensure_deployed()
    rec = build_canonical_record(platform="ev.com", post_url="https://ev.com/1", title="E", caption="v", image_sha256="e1")
    h = hash_canonical(rec)
    receipt = client.store(h)
    assert receipt["tx_hash"].startswith("0x") and len(receipt["tx_hash"]) == 66
    assert receipt["timestamp"] > 0
    ev = client.find_record_event(h)
    assert ev is not None
    assert ev["tx_hash"] == receipt["tx_hash"]
    assert ev["block_number"] == receipt["block_number"]
    assert client.find_record_event("cd" * 32) is None


def test_chain_info_reports_ephemeral_flag():
    from src.blockchain.client import VerificationRegistryClient, get_web3, is_ephemeral

    w3 = get_web3(rpc_url="http://127.0.0.1:1")  # unreachable → eth-tester
    assert is_ephemeral(w3)
    client = VerificationRegistryClient(w3)
    client.ensure_deployed()
    info = client.chain_info()
    assert info["ephemeral"] is True and info["contract_address"].startswith("0x")
