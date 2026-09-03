"""src.pipeline — end-to-end face → reverse-image search → face match → hash → blockchain → verify."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.blockchain.client import VerificationRegistryClient, get_web3, is_ephemeral
from src.config import Config
from src.extraction.post_extractor import download_image, enrich_result, is_social
from src.face.detector import detect_faces, largest_face
from src.face.matcher import cosine_similarity
from src.search.base import SearchResult
from src.search.provider import get_provider
from src.verification import phash as phash_mod
from src.verification.canonicalizer import build_canonical_record, canonicalize
from src.verification.hasher import hash_canonical

logger = logging.getLogger(__name__)

_ZERO_TX = "0x" + "00" * 32


# ── console helpers ──────────────────────────────────────────────────


def _step(n: int, total: int, msg: str) -> None:
    print(f"\n[{n}/{total}] {msg}...")


def _ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def _warn(msg: str) -> None:
    print(f"  ! {msg}")


def _rule(ch: str = "=") -> None:
    print(ch * 60)


# ── record helpers ───────────────────────────────────────────────────


def resolve_record_path(record_id: str) -> Path:
    """Accept a record id, 'latest', or a path to a JSON file."""
    rid = record_id.strip()
    if rid.lower() in ("latest", "last"):
        p = Config.data_dir() / "latest_record.json"
        if not p.exists():
            raise FileNotFoundError("No record yet — run `python main.py identify --image <path>` first.")
        return p
    p = Config.records_dir() / f"{rid}.json"
    if p.exists():
        return p
    alt = Path(rid)
    if alt.exists() and alt.suffix == ".json":
        return alt
    raise FileNotFoundError(f"Record not found: {rid} (looked in {Config.records_dir()})")


def list_records() -> list[dict]:
    out = []
    for p in sorted(Config.records_dir().glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            r = json.loads(p.read_text())
        except Exception:  # noqa: BLE001
            continue
        bm = r.get("best_match", {})
        out.append(
            {
                "record_id": r.get("record_id", p.stem),
                "created_at": r.get("created_at"),
                "platform": bm.get("platform", ""),
                "post_url": bm.get("post_url", ""),
                "similarity": bm.get("similarity"),
                "data_hash": r.get("data_hash", ""),
                "tx_hash": r.get("blockchain", {}).get("tx_hash", ""),
                "path": str(p),
            }
        )
    return out


def tamper_record(record_id: str, field: str = "caption", value: str | None = None, out_id: str | None = None) -> Path:
    """Write a modified copy of a record (for the tamper demo). Returns the new record path."""
    src = resolve_record_path(record_id)
    rec = json.loads(src.read_text())
    canonical = rec.get("canonical") or {}
    if field not in canonical:
        raise ValueError(f"Field '{field}' not in canonical record. Choose one of: {', '.join(canonical)}")
    original = canonical[field]
    canonical[field] = value if value is not None else (original + " [edited]" if original else "TAMPERED")
    new_id = out_id or f"{rec.get('record_id', src.stem)}-tampered"
    rec["record_id"] = new_id
    rec["tampered_from"] = src.stem
    rec["tamper_note"] = {"field": field, "original": original, "modified": canonical[field]}
    dst = Config.records_dir() / f"{new_id}.json"
    dst.write_text(json.dumps(rec, indent=2))
    return dst


# ── candidate ordering / filtering ──────────────────────────────────


def _blocked(domain: str) -> bool:
    d = (domain or "").lower()
    return any(b in d for b in Config.SEARCH_DOMAIN_BLOCKLIST)


def _order_results(results: list[SearchResult]) -> list[SearchResult]:
    """Drop blocklisted domains; optionally move social/wiki hosts first (stable sort)."""
    kept = [r for r in results if not _blocked(r.source)]
    if Config.PREFER_SOCIAL:
        kept.sort(key=lambda r: 0 if (is_social(r.source) or "wiki" in r.source) else 1)
    return kept


# ── blockchain helpers ──────────────────────────────────────────────


def _attach_or_deploy(w3, verbose: bool) -> VerificationRegistryClient:
    client = VerificationRegistryClient(w3, address=Config.CONTRACT_ADDRESS or None)
    if client.address and client.has_code():
        return client
    if verbose and client.address:
        _warn(f"CONTRACT_ADDRESS {client.address} has no code on chain {w3.eth.chain_id} — redeploying")
    if verbose:
        print("  → Deploying VerificationRegistry contract...")
    addr = client.ensure_deployed(private_key=Config.PRIVATE_KEY or None)
    if verbose:
        _ok(f"Contract deployed at {addr}")
    return client


# ── identify ─────────────────────────────────────────────────────────


def identify_pipeline(
    image_path: str,
    threshold: float | None = None,
    max_results: int | None = None,
    search_provider: str | None = None,
    image_url: str | None = None,
    w3=None,
    verbose: bool = True,
) -> dict:
    """Run the full pipeline and persist a record. Returns the record dict."""
    cfg_threshold = threshold if threshold is not None else Config.FACE_SIMILARITY_THRESHOLD
    cfg_max = max_results if max_results is not None else Config.SEARCH_MAX_RESULTS
    total = 6

    if verbose:
        _rule()
        print(" FACE IDENTIFICATION & BLOCKCHAIN VERIFICATION")
        _rule()

    # 1. load
    if verbose:
        _step(1, total, "Loading input image")
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"Input image not found: {p}")
    if verbose:
        _ok(f"Image: {p} ({p.stat().st_size / 1024:.1f} KB)")
    try:
        query_phash = phash_mod.phash(p)
    except Exception:  # noqa: BLE001
        query_phash = ""

    # 2. detect
    if verbose:
        _step(2, total, "Detecting face")
    faces = detect_faces(str(p), det_size=Config.FACE_DETECTION_SIZE, model_pack=Config.FACE_MODEL)
    if not faces:
        raise ValueError(f"No face detected in {p}. Try a clearer front-facing photo (face > 80 px, good lighting).")
    query_face = largest_face(faces)
    assert query_face is not None
    if verbose:
        for i, f in enumerate(faces):
            _ok(f"Face {i + 1}: bbox=({f.bbox.x1},{f.bbox.y1},{f.bbox.x2},{f.bbox.y2}) conf={f.det_score:.2f}")
        if len(faces) > 1:
            _warn(f"{len(faces)} faces detected — using the largest as the query face")

    # 3. embed
    query_emb = query_face.embedding
    if verbose:
        _step(3, total, "Generating face embedding")
        _ok(f"ArcFace embedding: dim={len(query_emb)}, L2 norm={float((query_emb**2).sum() ** 0.5):.3f}")
        if query_phash:
            _ok(f"Perceptual hash (pHash): {query_phash}")

    # 4. search
    if verbose:
        _step(4, total, "Reverse-image search on the web")
    provider = get_provider(search_provider, image_url=image_url or Config.INPUT_IMAGE_URL or None)
    if verbose:
        print(f"  → Provider: {provider.name}")
    # Over-fetch so that domain filtering / social-first ordering has something to work with,
    # then evaluate only the top `cfg_max` candidates.
    try:
        raw_results = provider.search(str(p), max_results=min(cfg_max * 2, 40))
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Web search failed ({provider.name}): {exc}") from exc
    if not raw_results:
        raise RuntimeError(
            f"Search returned 0 results (provider={provider.name}). The image may not appear anywhere public; "
            "try another image, --provider serpapi, or --image-url."
        )
    results = _order_results(raw_results)[:cfg_max]
    dropped = len(raw_results) - len(_order_results(raw_results))
    if verbose:
        _ok(
            f"Search completed — {len(raw_results)} page(s) found"
            + (f", {dropped} skipped by domain blocklist" if dropped else "")
            + f"; evaluating top {len(results)}"
        )
        if getattr(provider, "last_query_url", None):
            print(f"  → Query: {provider.last_query_url}")
        for i, r in enumerate(results[:8]):
            print(f"     {i + 1}. [{r.source}] {r.title[:58]} — {r.url[:80]}")
    if not results:
        raise RuntimeError("All search results were filtered out by SEARCH_DOMAIN_BLOCKLIST.")

    # 5. compare
    if verbose:
        _step(5, total, "Comparing faces in candidate pages")
    candidates_dir = Config.candidates_dir()
    scored: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for idx, res in enumerate(results):
        img_url = res.image_url or res.thumbnail_url
        if not img_url or not img_url.startswith("http"):
            skipped.append({"url": res.url, "reason": "no image url"})
            continue
        try:
            local_path, image_sha = download_image(img_url, candidates_dir)
        except Exception as exc:  # noqa: BLE001
            skipped.append({"url": res.url, "reason": f"download failed: {exc}"})
            if verbose:
                print(f"     · {idx + 1}. {res.source} — download failed, skipped")
            continue
        try:
            c_faces = detect_faces(str(local_path), det_size=Config.FACE_DETECTION_SIZE, model_pack=Config.FACE_MODEL)
        except Exception as exc:  # noqa: BLE001
            skipped.append({"url": res.url, "reason": f"unreadable image: {exc}"})
            if verbose:
                print(f"     · {idx + 1}. {res.source} — image not readable (site served a page instead of the image), skipped")
            continue
        if not c_faces:
            skipped.append({"url": res.url, "reason": "no face in image"})
            if verbose:
                print(f"     · {idx + 1}. {res.source} — no face detected, skipped")
            continue
        c_face = largest_face(c_faces)
        assert c_face is not None
        score = cosine_similarity(query_emb, c_face.embedding)
        try:
            enriched = enrich_result(res)
        except Exception:  # noqa: BLE001
            enriched = {
                "platform": res.source,
                "domain": res.source,
                "post_url": res.url,
                "title": res.title,
                "caption": "",
                "author": "",
                "published_at": "",
            }
        try:
            c_phash = phash_mod.phash(local_path)
        except Exception:  # noqa: BLE001
            c_phash = ""
        scored.append(
            {
                **enriched,
                "image_url": img_url,
                "local_path": str(local_path),
                "image_sha256": image_sha,
                "image_phash": c_phash,
                "similarity": float(score),
                "bbox": asdict(c_face.bbox),
                "det_score": float(c_face.det_score),
                "social": is_social(res.source),
                "result": res,
            }
        )
        if verbose:
            flag = "✓ match" if score >= cfg_threshold else "below threshold"
            print(f"     · {idx + 1}. {res.source:<28} similarity={score * 100:5.1f}%  {flag}")

    if not scored:
        raise RuntimeError(
            "No candidate page yielded a detectable face (downloads failed or images had no face). Try another image or provider."
        )

    # rank: similarity, plus a small bonus for social-media hosts that already pass the threshold
    def _rank(c: dict[str, Any]) -> float:
        bonus = Config.SOCIAL_BONUS if (Config.PREFER_SOCIAL and c["social"] and c["similarity"] >= cfg_threshold) else 0.0
        return c["similarity"] + bonus

    scored.sort(key=_rank, reverse=True)
    best = scored[0]
    is_match = best["similarity"] >= cfg_threshold

    if verbose:
        print("\n" + "-" * 60)
        print("MATCHING CONTENT")
        print("-" * 60)
        print(f"Platform       : {best['platform']}")
        print(f"Title          : {best['title'][:90]}")
        print(f"URL            : {best['post_url']}")
        print(f"Image URL      : {best['image_url'][:100]}")
        if best.get("author"):
            print(f"Author         : {best['author']}")
        if best.get("published_at"):
            print(f"Published      : {best['published_at']}")
        print(f"Similarity     : {best['similarity'] * 100:.2f}%  (threshold {cfg_threshold * 100:.0f}%)")
        print(f"Face match     : {'YES' if is_match else 'NO — best candidate is below threshold'}")
        if best["social"] and Config.PREFER_SOCIAL and Config.SOCIAL_BONUS:
            print(f"Ranking        : social-media host, +{Config.SOCIAL_BONUS:.2f} ranking bonus applied")
        print(f"Image SHA-256  : {best['image_sha256']}")
        print(f"Local copy     : {best['local_path']}")
        print("-" * 60)
        if not is_match:
            _warn("Recording the best candidate anyway; the record is flagged is_match=false.")

    # 6. canonicalize + hash + chain
    if verbose:
        _step(6, total, "Creating blockchain verification record")
    canonical = build_canonical_record(
        platform=best["platform"],
        post_url=best["post_url"],
        title=best["title"],
        caption=best.get("caption", ""),
        image_sha256=best["image_sha256"],
        author=best.get("author", ""),
        published_at=best.get("published_at", ""),
        image_url=best["image_url"],
    )
    canonical_bytes = canonicalize(canonical)
    data_hash_hex = hash_canonical(canonical)
    if verbose:
        _ok(f"Canonical JSON ({len(canonical_bytes)} bytes): {canonical_bytes[:110].decode(errors='ignore')}…")
        _ok(f"SHA-256 fingerprint: 0x{data_hash_hex}")

    if w3 is None:
        w3 = get_web3()
    try:
        client = _attach_or_deploy(w3, verbose)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Blockchain deploy failed: {exc}") from exc

    already_stored = False
    try:
        receipt = client.store(data_hash_hex, private_key=Config.PRIVATE_KEY or None)
    except Exception as exc:  # noqa: BLE001
        exists, ts = client.verify(data_hash_hex)
        if not exists:
            raise RuntimeError(f"Blockchain store failed: {exc}") from exc
        already_stored = True
        ev = client.find_record_event(data_hash_hex) or {}
        receipt = {
            "tx_hash": ev.get("tx_hash", _ZERO_TX),
            "block_number": ev.get("block_number"),
            "gas_used": 0,
            "status": 1,
            "timestamp": ev.get("timestamp", ts),
            "sender": ev.get("sender"),
        }
        if verbose:
            _warn(
                f"This fingerprint is already on-chain (stored at ts={receipt['timestamp']}) — reusing the original transaction"
            )

    if verbose:
        _ok("Fingerprint anchored on-chain" if not already_stored else "Fingerprint confirmed on-chain")
        print(f"\n  Transaction    : {receipt['tx_hash']}")
        print(f"  Block          : {receipt['block_number']}")
        print(f"  Block time     : {receipt.get('timestamp')}")
        print(f"  Contract       : {client.address}")
        print(f"  Chain          : id={w3.eth.chain_id} {'(eth-tester, ephemeral)' if is_ephemeral(w3) else Config.RPC_URL}")

    record_id = uuid.uuid4().hex[:8]
    record = {
        "record_id": record_id,
        "created_at": int(time.time()),
        "image_path": str(p),
        "image_phash": query_phash,
        "query_face": {
            "bbox": asdict(query_face.bbox),
            "det_score": float(query_face.det_score),
            "embedding_dim": int(len(query_emb)),
        },
        "search": {
            "provider": provider.name,
            "query_url": getattr(provider, "last_query_url", None),
            "results_count": len(raw_results),
            "evaluated": len(scored),
            "skipped": skipped,
        },
        "best_match": {
            "platform": best["platform"],
            "domain": best.get("domain", ""),
            "post_url": best["post_url"],
            "title": best["title"],
            "caption": best.get("caption", ""),
            "author": best.get("author", ""),
            "published_at": best.get("published_at", ""),
            "image_url": best["image_url"],
            "image_sha256": best["image_sha256"],
            "image_phash": best.get("image_phash", ""),
            "similarity": best["similarity"],
            "threshold": float(cfg_threshold),
            "is_match": bool(is_match),
            "local_path": best["local_path"],
            "bbox": best["bbox"],
        },
        "canonical": canonical,
        "canonical_bytes_hex": canonical_bytes.hex(),
        "data_hash": "0x" + data_hash_hex,
        "data_hash_hex": data_hash_hex,
        "blockchain": {
            "contract_address": client.address,
            "tx_hash": receipt["tx_hash"],
            "block_number": receipt["block_number"],
            "block_timestamp": receipt.get("timestamp"),
            "sender": receipt.get("sender"),
            "chain_id": int(w3.eth.chain_id),
            "rpc_url": "eth-tester (in-memory)" if is_ephemeral(w3) else Config.RPC_URL,
            "ephemeral": is_ephemeral(w3),
            "already_stored": already_stored,
        },
        "ranked_candidates": [
            {
                "source": c["result"].source,
                "platform": c["platform"],
                "title": c["title"][:120],
                "url": c["post_url"],
                "similarity": c["similarity"],
                "is_match": bool(c["similarity"] >= cfg_threshold),
            }
            for c in scored[:10]
        ],
    }
    rec_path = Config.records_dir() / f"{record_id}.json"
    rec_path.write_text(json.dumps(record, indent=2))
    (Config.data_dir() / "latest_record.json").write_text(json.dumps(record, indent=2))

    if verbose:
        print()
        _rule()
        print("✓ VERIFICATION RECORD CREATED")
        _rule()
        print(f"Record ID      : {record_id}")
        print(f"Record file    : {rec_path}")
        print(f"Verify with    : python main.py verify --record {record_id}")
        print(f"Tamper demo    : python main.py tamper --record {record_id}")
        if is_ephemeral(w3):
            _warn("Chain is in-memory: start Ganache/Anvil and set RPC_URL for verification across runs.")
        _rule()
    return record


# ── verify ───────────────────────────────────────────────────────────


def verify_pipeline(record_id: str, refetch: bool = False, w3=None, verbose: bool = True) -> dict:
    """Re-hash a stored record and compare with the on-chain fingerprint.

    refetch=True re-downloads the matched image from the web, recomputes its SHA-256 and rebuilds the
    canonical record from live data — proving the *content* (not just the local file) is unchanged.
    """
    if verbose:
        _rule()
        print(" BLOCKCHAIN VERIFICATION" + ("  (re-fetching live content)" if refetch else ""))
        _rule()

    rec_path = resolve_record_path(record_id)
    record = json.loads(rec_path.read_text())
    canonical = dict(record.get("canonical") or {})
    if not canonical:
        raise ValueError(f"Record {record_id} has no canonical data")
    stored_hex = (record.get("data_hash_hex") or record.get("data_hash", "")).lower().removeprefix("0x")

    refetch_info: dict | None = None
    if refetch:
        img_url = canonical.get("image_url", "")
        if not img_url:
            raise ValueError("Record has no image_url to re-fetch")
        local, live_sha = download_image(img_url, Config.candidates_dir() / "refetch")
        refetch_info = {
            "image_url": img_url,
            "live_image_sha256": live_sha,
            "recorded_image_sha256": canonical.get("image_sha256", ""),
        }
        try:
            live_ph = phash_mod.phash(local)
            rec_ph = record.get("best_match", {}).get("image_phash", "")
            if rec_ph and live_ph:
                refetch_info["phash_similarity"] = phash_mod.similarity(live_ph, rec_ph)
        except Exception:  # noqa: BLE001
            pass
        canonical["image_sha256"] = live_sha
        if verbose:
            _ok(f"Re-downloaded {img_url[:80]}")
            _ok(f"Live image SHA-256: {live_sha}")

    current_hex = hash_canonical(canonical)
    if verbose:
        print(f"Record ID      : {record.get('record_id')}")
        print(f"Record file    : {rec_path}")
        if record.get("tamper_note"):
            tn = record["tamper_note"]
            print(f"Tamper note    : field '{tn['field']}' changed {tn['original']!r} → {tn['modified']!r}")
        print(f"Post           : [{canonical.get('platform')}] {canonical.get('post_url')}")
        print(f"\nRECORDED HASH  : 0x{stored_hex}")
        print(f"CURRENT HASH   : 0x{current_hex}")

    # chain
    if w3 is None:
        w3 = get_web3()
    contract_addr = record.get("blockchain", {}).get("contract_address") or Config.CONTRACT_ADDRESS
    client = VerificationRegistryClient(w3, address=contract_addr or None)
    on_chain_available = bool(contract_addr) and client.has_code()

    hashes_match = current_hex == stored_hex
    current_on_chain = False
    recorded_on_chain = False
    timestamp = 0
    event = None
    if on_chain_available:
        current_on_chain, timestamp = client.verify(current_hex)
        recorded_on_chain, _ = client.verify(stored_hex)
        if current_on_chain:
            event = client.find_record_event(current_hex)
        verified = current_on_chain
        mode = "on-chain"
    else:
        verified = hashes_match
        mode = "local-only"
        if verbose:
            _warn("Contract not found on the connected chain (in-memory chains vanish between runs).")
            print("    Falling back to comparing the recomputed hash with the hash saved in the record.")
            print("    For true on-chain verification: npx ganache --port 8545  and set RPC_URL in .env")

    if verbose:
        print(f"\nChain          : id={w3.eth.chain_id}  contract={contract_addr or '-'}  mode={mode}")
        if on_chain_available:
            print(f"Current hash on-chain  : {current_on_chain}" + (f"  (stored ts={timestamp})" if current_on_chain else ""))
            print(f"Recorded hash on-chain : {recorded_on_chain}")
            if event:
                print(f"Original tx            : {event['tx_hash']}  block #{event['block_number']}")
        print(f"Hashes match           : {hashes_match}")
        if refetch_info:
            same = refetch_info["live_image_sha256"] == refetch_info["recorded_image_sha256"]
            print(
                f"Live image unchanged   : {same}"
                + (
                    f"  (pHash similarity {refetch_info['phash_similarity'] * 100:.1f}%)"
                    if "phash_similarity" in refetch_info
                    else ""
                )
            )
        print()
        _rule()
        if verified:
            print(
                "✓ VERIFIED — fingerprint matches the blockchain record"
                if mode == "on-chain"
                else "✓ VERIFIED (local) — fingerprint matches the saved record"
            )
            print("  No modification detected.")
        else:
            print("✗ TAMPERED — fingerprint does not match")
            if not hashes_match:
                print("  The data hashes differently from when it was recorded — content was modified.")
            if on_chain_available and not current_on_chain:
                print("  The recomputed fingerprint is NOT on the blockchain.")
            if on_chain_available and recorded_on_chain:
                print("  (The original fingerprint is still on-chain — the record file, not the chain, was altered.)")
        _rule()

    return {
        "record_id": record.get("record_id"),
        "record_path": str(rec_path),
        "canonical": canonical,
        "recorded_hash": "0x" + stored_hex,
        "current_hash": "0x" + current_hex,
        "hashes_match": hashes_match,
        "mode": mode,
        "on_chain_available": on_chain_available,
        "current_hash_on_chain": current_on_chain,
        "recorded_hash_on_chain": recorded_on_chain,
        "on_chain_timestamp": timestamp,
        "event": event,
        "refetch": refetch_info,
        "verified": verified,
        "status": "VERIFIED" if verified else "TAMPERED",
    }
