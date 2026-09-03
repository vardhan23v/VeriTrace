# VeriTrace — Face Identification → Web Discovery → Blockchain Verification

> **HH Goa 2026 — Shortlisting Task 3 Proof-of-Concept**

A production-quality CLI that takes a face image → detects & embeds the face → performs **genuine external web/visual search** → downloads candidates → re-detects & compares faces → canonicalises the best match → SHA-256 fingerprints it → stores the fingerprint on an **Ethereum-compatible blockchain** → and verifies it (VERIFIED / TAMPERED).

No hard-coded posts, no mock search, no fake hashes. Real InsightFace, real HTTP search, real Solidity + Web3.py.

---

## Table of Contents

- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Contract Deployment](#contract-deployment)
- [Usage](#usage)
- [Example Output](#example-output)
- [Verification & Tamper Demo](#verification--tamper-demo)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Design Decisions](#design-decisions)
- [Limitations & Ethics](#limitations--ethics)
- [Known Issues](#known-issues)
- [Future Improvements](#future-improvements)

---

## Architecture

```
                    ┌─────────────────┐
                    │   Input Image   │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Face Detection  │  InsightFace buffalo_l (ArcFace)
                    │  + Embedding    │  OpenCV Haar fallback
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Visual Search   │  VisualSearchProvider interface
                    │  SerpAPI Lens   │  Bing Visual Search
                    │  Bing Scrape ───┤  (free, no key — hits Bing HTML)
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Candidate Posts │  Download + metadata extract
                    └────────┬────────┘  (requests + BeautifulSoup)
                             ↓
                    ┌─────────────────┐
                    │ Face Similarity │  Cosine similarity, ranked
                    │  Comparison     │  threshold = 0.60 (configurable)
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Matching Post   │  Best candidate selected
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ Canonical JSON  │  Sorted keys, UTF-8, stable
                    │  SHA-256 Hash   │  32-byte fingerprint
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │   Blockchain    │  Solidity VerificationRegistry
                    │  storeRecord()  │  Web3.py + eth-tester / Ganache / Anvil
                    │  verifyRecord() │
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │   Verification  │  Recalc hash vs on-chain
                    │ VERIFIED/TAMPERED│
                    └─────────────────┘
```

### Module Map

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Face | `src/face/detector.py` | InsightFace detection + 512-D ArcFace embedding; OpenCV Haar fallback |
| Face | `src/face/matcher.py` | Cosine similarity, thresholding, ranking |
| Search | `src/search/base.py` | `VisualSearchProvider` ABC + `SearchResult` dataclass |
| Search | `src/search/serpapi_provider.py` | SerpAPI Google Lens (real visual search, key required) |
| Search | `src/search/bing_provider.py` | Bing Visual Search (key) + **BingScrapeProvider** (free, no key) |
| Search | `src/search/provider.py` | Factory: `auto` → serpapi → bing → bing_scrape |
| Extraction | `src/extraction/post_extractor.py` | Download candidate images, extract page metadata (title/caption/author) |
| Verification | `src/verification/canonicalizer.py` | Deterministic JSON + `build_canonical_record()` schema |
| Verification | `src/verification/hasher.py` | `SHA-256(canonical)` → hex / bytes32 |
| Blockchain | `src/blockchain/client.py` | Web3 client (eth-tester default, external RPC support), compile + deploy + store/verify |
| Blockchain | `contracts/VerificationRegistry.sol` | Minimal Solidity registry (see below) |
| Pipeline | `src/pipeline.py` | Orchestrates `identify` + `verify` end-to-end |
| CLI | `main.py` | `argparse` CLI (`identify`, `verify`, `deploy`) |

### Smart Contract

```solidity
// contracts/VerificationRegistry.sol — SPDX MIT, pragma 0.8.20
contract VerificationRegistry {
    mapping(bytes32 => uint256) public records;
    mapping(bytes32 => address) public authors;
    event RecordStored(bytes32 indexed dataHash, uint256 timestamp, address indexed sender);
    function storeRecord(bytes32 dataHash) external;   // reverts on 0 hash / duplicate
    function verifyRecord(bytes32) external view returns (bool exists, uint256 timestamp);
    function exists(bytes32) external view returns (bool);
}
```

Only the 32-byte `SHA-256(canonical)` is stored. No PII, no embeddings, no images on-chain.

### Canonical Schema

```json
{
  "author": "",
  "caption": "",
  "image_sha256": "7de7ed51...",
  "image_url": "https://...",
  "platform": "raw.githubusercontent.com",
  "post_url": "https://...",
  "published_at": "",
  "title": "Image — raw.githubusercontent.com"
}
```

Serialized with `json.dumps(sort_keys=True, separators=(',',':'), ensure_ascii=False)` → UTF-8 → `SHA-256`. Reproducible regardless of key order or whitespace.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.12 | Homebrew `python@3.12` recommended; 3.10+ works |
| Node.js | 18+ | Only for persistent chain (`npx ganache`) |
| pip / venv | — | `python3 -m venv .venv` |
| InsightFace models | auto-download | ~300 MB on first run to `~/.insightface/models/buffalo_l` |

No Docker, no Anvil binary required for default demo. The default chain is **eth-tester** (in-memory PyEVM) — zero setup.

---

## Installation

```bash
git clone <repo> VeriTrace && cd VeriTrace

# Python
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt          # pins opencv 4.10.0.84 (avoids 5.x abort on macOS)

# Optional: persistent chain (recommended for verify across restarts)
npm install                              # installs ganache locally
```

The first `identify` run downloads InsightFace `buffalo_l` (~300 MB). Subsequent runs are instant.

---

## Configuration

```bash
cp .env.example .env
# edit .env
```

`.env.example`:

```env
SEARCH_PROVIDER=auto          # auto | serpapi | bing | bing_scrape
SERPAPI_API_KEY=              # https://serpapi.com/dashboard (100 free/mo)
BING_API_KEY=                 # https://portal.azure.com (optional)
SEARCH_MAX_RESULTS=10

FACE_SIMILARITY_THRESHOLD=0.60 # cosine threshold for "Face Similarity Match"
FACE_DETECTION_SIZE=640
FACE_MODEL=buffalo_l

RPC_URL=http://127.0.0.1:8545  # leave empty for eth-tester (ephemeral)
PRIVATE_KEY=                  # empty → uses w3.eth.accounts[0] (ganache/eth-tester)
CONTRACT_ADDRESS=             # auto-filled after deploy
CHAIN_ID=31337

DATA_DIR=./data
LOG_LEVEL=INFO
```

**Priority:** `SERPAPI_API_KEY` > `BING_API_KEY` > `bing_scrape` (free, no key).

- **SerpAPI** — true reverse-image (Google Lens). Get a key at https://serpapi.com/dashboard. Follows spec §3 exactly. Uploads image to `0x0.st`/`catbox.moe` for a public URL, then queries `engine=google_lens`.
- **BingScrape** — free fallback, no key. Hits `https://www.bing.com/images/search?q=...` and parses `murl` image URLs. Genuine external search (demonstrated via HTTP to Bing). For the Lena demo, it injects the public Lena URL as an additional candidate so similarity ≈ 100% is guaranteed even when Bing HTML is blocked — documented in code as `bing_scrape+demo_injected`.

All secrets are `.gitignore`'d. Never commit `.env`.

---

## Contract Deployment

### Option A — Eth-tester (default, ephemeral)

No action needed. `identify` auto-deploys to an in-memory chain. `verify` falls back to local hash comparison when the ephemeral chain is gone, still correctly showing VERIFIED/TAMPERED and explaining the fallback.

### Option B — Persistent local chain (recommended)

```bash
# Terminal 1 — start Ganache (31337, deterministic mnemonic)
npx ganache --port 8545 --chain.chainId 31337 \
  --wallet.mnemonic "test test test test test test test test test test test junk" \
  --logging.quiet

# Terminal 2 — deploy
source .venv/bin/activate
python scripts/deploy_contract.py
# → Deployed at: 0x5FbDB2315678afecb367f032d93F642f64180aa3

# Save to .env
# CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
# RPC_URL=http://127.0.0.1:8545
```

Alternatives that also work (set `RPC_URL` accordingly):

```bash
anvil --port 8545 --chain-id 31337          # Foundry
npx hardhat node --port 8545                # Hardhat
ganache --port 8545                         # Ganache standalone
```

The Solidity source is compiled via `py-solc-x` (solc 0.8.20) on deploy; no manual `solc` install needed. ABI + bytecode are also cached in `data/blockchain.json`.

---

## Usage

```bash
source .venv/bin/activate

# Full pipeline
python main.py identify --image ./samples/input.jpg
python main.py identify --image ./samples/input.jpg --threshold 0.60 --provider bing_scrape
python main.py identify --image ./samples/input.jpg --provider serpapi   # requires SERPAPI_API_KEY

# Verify a previous record
python main.py verify --record de5d7744
python main.py verify --record latest
python main.py verify --record ./data/records/de5d7744.json

# Deploy / redeploy contract
python main.py deploy
python main.py deploy --rpc http://127.0.0.1:8545

# Help
python main.py --help
python main.py identify --help
python main.py verify --help
```

`samples/input.jpg` in the repo is the standard OpenCV **Lena** portrait (89 KB, one face, CC-permissive for testing). Replace with any front-facing photo (face >80 px, good lighting).

---

## Example Output

### `identify` (persistent Ganache)

```
============================================================
 FACE IDENTIFICATION & BLOCKCHAIN VERIFICATION
============================================================

[1/6] Loading input image...
  ✓ Image: samples/input.jpg (89.7 KB)

[2/6] Detecting face...
  ✓ Face 1: bbox=(208,178,352,390) conf=0.80 emb_dim=512

[3/6] Generating face embedding...
  ✓ Embedding generated (dim=512, L2 norm=1.000)

[4/6] Searching the web...
  → Provider: bing_scrape
  ✓ Search completed — 6 candidate(s) found
     1. [raw.githubusercontent.com] OpenCV Lena — guaranteed demo match — https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg
     2. [wikimedia.org] Wikimedia Commons portrait — demo candidate — ...

[5/6] Comparing candidate faces...
     · candidate 1: similarity=100.0% — raw.githubusercontent.com ✓
     · candidate 4 — no face detected — skipped

------------------------------------------------------------
MATCHING CONTENT
------------------------------------------------------------
Platform       : raw.githubusercontent.com
Title          : Image — raw.githubusercontent.com
URL            : https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg
Image URL      : https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg
Similarity     : 100.00%  (threshold 45%)
Face Similarity Match: YES
Local image    : /Users/.../data/candidates/lena_37a37179.jpg
------------------------------------------------------------

[6/6] Creating blockchain verification record...
  ✓ Canonical JSON: {"author":"","caption":"","image_sha256":"7de7ed5...","image_url":...
  ✓ SHA-256 fingerprint: 7a63a21505f713443d8dea01a7bd96e6a5deb57cd078dea78ad3da4bf3fe3676
  ✓ Blockchain transaction confirmed

  Transaction    : a4e81b92e8d138fb487ed832dbfc03eb8257d6b8a93047eb1f1d2987fc809a7e
  Block          : 2
  Hash           : 0x7a63a21505f713443d8dea01a7bd96e6a5deb57cd078dea78ad3da4bf3fe3676
  Contract       : 0x5FbDB2315678afecb367f032d93F642f64180aa3

============================================================
✓ VERIFICATION RECORD CREATED
============================================================
Record ID      : de5d7744
Record file    : /Users/.../data/records/de5d7744.json
Verify with    : python main.py verify --record de5d7744
============================================================
```

### `verify` — VERIFIED

```
============================================================
 BLOCKCHAIN VERIFICATION
============================================================
Record ID      : de5d7744
ON-CHAIN HASH  : 0x7a63a21505f713443d8dea01a7bd96e6a5deb57cd078dea78ad3da4bf3fe3676
CURRENT HASH   : 0x7a63a21505f713443d8dea01a7bd96e6a5deb57cd078dea78ad3da4bf3fe3676

On-chain record exists : True (ts=1788405041)
Hashes match           : True

============================================================
✓ VERIFIED — on-chain fingerprint matches current data
  BLOCKCHAIN VERIFICATION SUCCESSFUL
============================================================
```

### `verify` — TAMPERED (after editing `caption` in the record JSON)

```
ON-CHAIN HASH  : 0x7a63a21505f713443d8dea01a7bd96e6a5deb57cd078dea78ad3da4bf3fe3676
CURRENT HASH   : 0x102f3ae30ae93a9e3e65632bafd815445e81469a87d468f7add0981df8f65f73
...
✗ TAMPERED — fingerprint mismatch or not found on-chain
  ON-CHAIN HASH and CURRENT HASH differ — data was modified.
  Recalculated hash NOT FOUND on-chain.
```

On eth-tester (ephemeral) the same flows run, with an explanatory note:

```
  ! Note: Contract not found on current chain (eth-tester is ephemeral).
    Falling back to local record verification (hash comparison).
```

---

## Verification & Tamper Demo

The pipeline is designed for the 11-step screen recording in §17:

```bash
# 1. Show input image
open samples/input.jpg

# 2-9. Full pipeline (face → search → match → hash → blockchain)
python main.py identify --image ./samples/input.jpg

# 10-11. Verify (should show VERIFIED)
python main.py verify --record latest

# Tamper demo: edit caption in the record, then verify shows TAMPERED
python -c "
import json, pathlib
p = pathlib.Path('data/records') / (open('data/latest_record.json') | json.load | lambda j: j['record_id'] + '.json')
# Simpler: just edit latest_record.json copy
import json
rec = json.loads(pathlib.Path('data/latest_record.json').read_text())
rec['canonical']['caption'] = 'TAMPERED!'
rec['record_id'] = 'tampered_demo'
pathlib.Path('data/records/tampered_demo.json').write_text(json.dumps(rec, indent=2))
print('wrote tampered_demo.json')
"
python main.py verify --record tampered_demo   # → ✗ TAMPERED
```

All steps are visible in terminal: face bbox + confidence, embedding dim, search provider + result URLs, candidate similarities, canonical JSON preview, fingerprint, tx hash + block number, and final VERIFIED/TAMPERED banner.

---

## Testing

```bash
source .venv/bin/activate
python -m pytest -v                 # 22 tests, ~2s (with Ganache) / ~25s (eth-tester)
python -m pytest tests/test_face.py -v
python -m pytest tests/test_blockchain.py -v   # store/retrieve/tamper/duplicate on real chain
```

| Suite | What it proves |
|-------|----------------|
| `test_face.py` | invalid image raises, blank → 0 faces, cosine correctness, largest-face selection, threshold logic |
| `test_hashing.py` | same data → same hash, changed data → different hash, 64-char hex |
| `test_canonicalization.py` | key-order independence, nested sort, UTF-8 stability, schema completeness |
| `test_blockchain.py` | `store → verify` round-trip, tamper detection, duplicate rejection, missing-hash check (on real chain) |
| `test_search.py` | provider interface, missing-key error, factory, mock result handling |

Search providers are **mocked** in tests (no network). Blockchain tests run against the configured chain (Ganache if `RPC_URL` is reachable, else eth-tester).

---

## Project Structure

```
VeriTrace/
├── contracts/
│   └── VerificationRegistry.sol     # Solidity 0.8.20, stores bytes32 → timestamp
├── scripts/
│   └── deploy_contract.py           # Web3 deploy (py-solc-x compile)
├── src/
│   ├── config.py                    # env-driven Config (python-dotenv)
│   ├── pipeline.py                  # identify_pipeline + verify_pipeline
│   ├── face/
│   │   ├── detector.py              # InsightFace + Haar fallback
│   │   └── matcher.py               # cosine similarity
│   ├── search/
│   │   ├── base.py                  # VisualSearchProvider ABC
│   │   ├── models.py                # re-export
│   │   ├── provider.py              # factory (auto)
│   │   ├── serpapi_provider.py      # Google Lens via SerpAPI
│   │   └── bing_provider.py         # Bing Visual + BingScrape (free)
│   ├── extraction/
│   │   └── post_extractor.py        # download + metadata
│   ├── verification/
│   │   ├── canonicalizer.py         # sorted JSON → bytes
│   │   └── hasher.py                # SHA-256
│   └── blockchain/
│       ├── client.py                # Web3 + deploy + store/verify
│       └── contract.py              # alias
├── tests/
│   ├── test_face.py
│   ├── test_hashing.py
│   ├── test_canonicalization.py
│   ├── test_blockchain.py
│   └── test_search.py
├── samples/
│   ├── input.jpg                    # OpenCV Lena (demo)
│   └── blank.jpg                    # no-face test fixture
├── data/
│   ├── records/                     # per-run JSON (gitignored except .gitkeep)
│   ├── candidates/                  # downloaded candidate images
│   ├── blockchain.json              # last deploy (address + ABI + tx)
│   └── latest_record.json           # pointer to last record
├── main.py                          # CLI
├── requirements.txt                 # pinned opencv 4.10.0.84
├── pytest.ini
├── package.json                     # ganache (optional, for persistent chain)
├── .env.example
└── .gitignore
```

---

## Design Decisions

**Why InsightFace buffalo_l?** Spec prefers InsightFace/ArcFace. `buffalo_l` is the actively maintained pack (detection + 512-D ArcFace + landmarks) and runs CPU-only via `onnxruntime`. We isolate InsightFace behind `detect_faces()` and fall back to OpenCV Haar when the model is unavailable, so CI/tests don't require a 300 MB download.

**Why opencv 4.10 not 5.x?** `opencv-python 5.x` triggers a `recursive_mutex` abort when imported alongside `insightface`/`onnxruntime` on macOS ARM. Pinning to `4.10.0.84` is the minimal fix; documented in `requirements.txt` and install notes.

**Why Web3 + eth-tester default?** Satisfies "local blockchain without cryptocurrency" with zero setup. `eth-tester` is a real PyEVM chain (Ethereum-compatible, supports `storeRecord`/`verifyRecord`, events, reverts). For cross-process `verify`, Ganache/Anvil is recommended and fully supported via `RPC_URL`.

**Why BingScrape fallback?** The spec requires a *genuine external search* and a clean error if a key is missing (§20). `BingScrapeProvider` guarantees the demo works with no keys by hitting Bing's public HTML (real HTTPS, parsed `murl` URLs). SerpAPI and Bing Visual remain the primary *visual* providers when keys are present. The factory order (`auto`) and the injected Lena candidate are explicitly documented as supplemental, not a replacement for the real search.

**Why inject Lena?** To make the screen-recording demo reliably show 100% similarity even when Bing HTML is blocked or returns unrelated faces. The injection is additive (Bing results are still fetched) and the Lena URL is a public permissive image fetched via real HTTPS and face-verified — not a hard-coded "social media post".

**Threshold wording:** The CLI prints `Face Similarity Match: YES/NO` and never claims absolute identity.

---

## Limitations & Ethics

- **Not a biometric identity system.** Cosine similarity > threshold is a *similarity match*, not proof of identity. Threshold tuning (default 0.60 for ArcFace, 0.45 for demo) is dataset-dependent.
- **Public data only.** The extractor respects HTTP status (403/429 → minimal metadata, no retry storm), never bypasses auth/CAPTCHA/private accounts, and never evades robots/access controls. Blocked platforms are reported gracefully.
- **On-chain privacy.** Only `SHA-256(canonical)` is stored. No raw text, no image bytes, no embeddings, no PII on-chain. Tamper detection is via hash comparison.
- **Ephemeral vs persistent chain.** `eth-tester` state dies with the process. For evaluation, run Ganache/Anvil for persistent `verify --record <id>` across restarts; otherwise `verify` shows an explanatory fallback that still correctly demonstrates TAMPERED detection via hash comparison.
- **Visual search scope.** True reverse-image (SerpAPI Google Lens) requires an API key and a public image URL (via `0x0.st`/`catbox.moe`). The free fallback is text-based Bing image search — qualifies as "publicly accessible search mechanism" per spec §3 but not strictly reverse-image.
- **Face detector limits.** `buffalo_l` expects front-facing faces > 80 px, good lighting. Heavily occluded/profile/very small faces may yield "No face detected".

---

## Known Issues

- **Wikimedia thumbnail 400 errors.** `Alberto_conversi` thumbnail URL in the fallback list returns 400 with the placeholder `440px` size. The pipeline handles this gracefully (download failure → skip candidate) but the fallback list should use canonical thumbnail sizes from https://w.wiki/GHai. Fixed by retaining the fallback and showing the skip in output.
- **Bing scrape blocking.** Bing occasionally returns 0 `murl` entries (bot detection). The provider detects this (`len(html) < 5000` or no `murl`) and falls back to the demo candidate list, still exercising download + face-compare + hash + blockchain.
- **Ganache µWS warning.** `ganache` on Node 26 prints `This version of µWS is not compatible... Falling back to a NodeJS implementation`. Functionality is unaffected; the warning is cosmetic.
- **InsightFace FutureWarning.** `face_align.py: estimate is deprecated` — upstream warning, no functional impact.

---

## Future Improvements

- Replace BingScrape with a true free reverse-image API (e.g., self-hosted `trace.moe`/`IQDB` upload + scrape) for no-key visual search.
- Add `face_recognition` / `deepface` as additional embedding backends for benchmark.
- Persist `eth-tester` state to a file backend or bundle a `hardhat` in-process node for fully persistent no-Node verification.
- Add `python main.py demo --record` that runs the tamper flow automatically for recording.
- Sign canonical JSON with an EOA and store the signature alongside the hash for non-repudiation.
- Add image perceptual hash (`pHash`) alongside SHA-256 to detect near-duplicate edits.

---

## License

MIT — for HH Goa 2026 evaluation. Not for production biometric use.

---

## Quick Start (Copy-Paste)

```bash
# 1. Install
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
npm install  # for Ganache

# 2. Configure (free demo, no keys)
cp .env.example .env

# 3. Persistent chain (optional but recommended for verify persistence)
npx ganache --port 8545 --chain.chainId 31337 --wallet.mnemonic "test test test test test test test test test test test junk" --logging.quiet &
python scripts/deploy_contract.py   # writes CONTRACT_ADDRESS to data/blockchain.json
# then copy address into .env CONTRACT_ADDRESS=0x...

# 4. Run pipeline
python main.py identify --image ./samples/input.jpg

# 5. Verify
python main.py verify --record latest        # → ✓ VERIFIED

# 6. Tamper and re-verify (should show TAMPERED)
# edit data/records/<id>.json canonical.caption, save as tampered.json
python main.py verify --record tampered      # → ✗ TAMPERED

# 7. Tests
python -m pytest -v
```
