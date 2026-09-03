<div align="center">

# VeriTrace

**Face Identification → Web Discovery → Blockchain Verification**

*Detect a face, find where it appears on the web, anchor a tamper-evident fingerprint on-chain, and prove it later.*

<a href="https://github.com/vardhan23v/VeriTrace/actions"><img src="https://img.shields.io/github/actions/workflow/status/vardhan23v/VeriTrace/ci.yml?branch=main&label=CI&logo=githubactions&logoColor=white&style=for-the-badge" height="28" alt="CI" /></a>
<a href="#testing"><img src="https://img.shields.io/badge/tests-35%20passing-brightgreen?logo=pytest&logoColor=white&style=for-the-badge" height="28" alt="Tests" /></a>
<a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white&style=for-the-badge" height="28" alt="Python" /></a>
<a href="contracts/VerificationRegistry.sol"><img src="https://img.shields.io/badge/solidity-0.8.20-363636?logo=solidity&logoColor=white&style=for-the-badge" height="28" alt="Solidity" /></a>
<a href="https://web3py.readthedocs.io/"><img src="https://img.shields.io/badge/web3.py-7.x-F16822?logo=ethereum&logoColor=white&style=for-the-badge" height="28" alt="web3.py" /></a>
<a href="https://github.com/deepinsight/insightface"><img src="https://img.shields.io/badge/InsightFace-ArcFace%20512--D-8A2BE2?style=for-the-badge" height="28" alt="InsightFace" /></a>
<a href="https://onnxruntime.ai/"><img src="https://img.shields.io/badge/ONNX%20Runtime-CPU-005CED?logo=onnx&logoColor=white&style=for-the-badge" height="28" alt="ONNX Runtime" /></a>
<a href="https://veritrace-dusky.vercel.app"><img src="https://img.shields.io/badge/showcase-Next.js%2015-000000?logo=nextdotjs&logoColor=white&style=for-the-badge" height="28" alt="Next.js" /></a>
<a href="https://veritrace-dusky.vercel.app"><img src="https://img.shields.io/badge/deployed-vercel-000000?logo=vercel&logoColor=white&style=for-the-badge" height="28" alt="Deployed on Vercel" /></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg?style=for-the-badge" height="28" alt="License: MIT" /></a>
<a href="https://docs.astral.sh/ruff/"><img src="https://img.shields.io/badge/code%20style-ruff-D7FF64?logo=ruff&logoColor=black&style=for-the-badge" height="28" alt="Code style: ruff" /></a>
<a href="https://github.com/vardhan23v/VeriTrace/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge" height="28" alt="PRs Welcome" /></a>

[**Live showcase**](https://veritrace-dusky.vercel.app) · [**Quick start**](#quick-start) · [**Commands**](#commands) · [**Example run**](#example-run) · [**Limitations**](#known-limitations)

</div>

> Built for **HH Goa 2026 — Shortlisting Task 3**: face scan → web / social-media search → blockchain upload & re-verification.

VeriTrace is a command-line pipeline that:

1. **Detects and embeds** the face in an input image (InsightFace RetinaFace + ArcFace, 512-D).
2. **Searches the web for that image** with a genuine reverse-image engine — Google Lens (SerpAPI), Bing Visual Search, or **Yandex with no API key**.
3. **Face-verifies every candidate page** by downloading its image and comparing embeddings with cosine similarity.
4. **Canonicalises the best match** (platform, URL, title, caption, author, date, image SHA-256) and fingerprints it with **SHA-256**.
5. **Anchors the fingerprint** in a Solidity `VerificationRegistry` on any EVM chain (Ganache, Anvil, testnet, or in-memory).
6. **Re-verifies** on demand — optionally re-downloading the live post image — and reports `✓ VERIFIED` or `✗ TAMPERED`.

Nothing is pre-picked: the search step is a live request for *your* image, and every candidate is fetched and face-compared before anything is hashed.

```bash
python main.py demo --image samples/lincoln.jpg --refetch    # identify → verify → tamper → verify, in one go
```

---

## Table of Contents

- [How it works](#how-it-works)
- [Quick start](#quick-start)
- [Commands](#commands)
- [Example run](#example-run)
- [Search providers](#search-providers)
- [Blockchain](#blockchain)
- [What is hashed](#what-is-hashed)
- [Testing](#testing)
- [Project structure](#project-structure)
- [Screen-recording script](#screen-recording-script)
- [Known limitations](#known-limitations)
- [Ethics](#ethics)

---

## How it works

```
 input.jpg
    │
    ▼
 ┌──────────────────────────┐   InsightFace buffalo_l: RetinaFace detection
 │ 1-3  Face detect + embed │   + ArcFace 512-D L2-normalised embedding
 └────────────┬─────────────┘   (OpenCV Haar fallback for tests / no model)
              ▼
 ┌──────────────────────────┐   Yandex "search by image" (keyless) → pages that
 │ 4  Reverse-image search  │   CONTAIN this image. Or SerpAPI Google Lens /
 └────────────┬─────────────┘   Bing Visual Search when keys are configured.
              ▼
 ┌──────────────────────────┐   Download each candidate image, detect its face,
 │ 5  Face-verify candidates│   cosine(query, candidate) ≥ threshold ⇒ match.
 └────────────┬─────────────┘   Best similarity wins (social hosts win ties).
              ▼
 ┌──────────────────────────┐   platform, post_url, title, caption, author,
 │ 6  Canonical JSON        │   published_at, image_url, image_sha256
 │    → SHA-256 fingerprint │   sorted keys · compact · UTF-8 → 32-byte hash
 └────────────┬─────────────┘
              ▼
 ┌──────────────────────────┐   VerificationRegistry.storeRecord(bytes32)
 │    Blockchain anchor     │   Ganache / Anvil / Hardhat / any EVM RPC,
 └────────────┬─────────────┘   or eth-tester in-memory (zero setup)
              ▼
 ┌──────────────────────────┐   re-hash record (optionally re-download the live
 │    verify                │   image) → verifyRecord(hash) → VERIFIED / TAMPERED
 └──────────────────────────┘
```

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Face | `src/face/detector.py` | InsightFace detection + 512-D ArcFace embedding; OpenCV Haar fallback |
| Face | `src/face/matcher.py` | Cosine similarity, threshold, ranking |
| Search | `src/search/yandex_provider.py` | **Keyless reverse-image search** (Yandex CBIR); upload or public URL |
| Search | `src/search/serpapi_provider.py` | Google Lens via SerpAPI (key) |
| Search | `src/search/bing_provider.py` | Bing Visual Search API (key); Bing *text* image search (opt-in only) |
| Search | `src/search/provider.py` | Factory: `auto` → serpapi → bing → **yandex** |
| Extraction | `src/extraction/post_extractor.py` | Download candidate images, extract title / caption / author / date, platform naming |
| Verification | `src/verification/canonicalizer.py` | Deterministic JSON schema |
| Verification | `src/verification/hasher.py` | SHA-256 → hex / bytes32 |
| Verification | `src/verification/phash.py` | Perceptual hash (informational; distinguishes re-encode from edit) |
| Blockchain | `contracts/VerificationRegistry.sol` | `storeRecord`, `verifyRecord`, `RecordStored` event |
| Blockchain | `src/blockchain/client.py` | Web3 client: compile (py-solc-x), deploy, store, verify, event lookup |
| Pipeline | `src/pipeline.py` | `identify_pipeline`, `verify_pipeline`, `tamper_record`, `list_records` |
| CLI | `main.py` | `identify · verify · tamper · demo · list · deploy` |

---

## Quick start

```bash
git clone https://github.com/vardhan23v/VeriTrace && cd VeriTrace
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # opencv is pinned to 4.10 (5.x aborts next to onnxruntime on macOS ARM)
cp .env.example .env                       # defaults are fine: keyless search, local chain

# optional but recommended: a persistent local chain so `verify` works across runs
npm install && npx ganache --port 8545 --chain.chainId 31337 --logging.quiet &
```

First `identify` downloads the InsightFace `buffalo_l` model pack (~300 MB) to `~/.insightface`.

```bash
python main.py demo --image samples/input.jpg
```

That single command runs the whole story: face → search → match → hash → chain → `VERIFIED` → tamper one field → `TAMPERED`.

**Better demo image.** `samples/input.jpg` is OpenCV's Lena, which reverse search associates with image-processing blogs (and a few sites you may not want on a recording; those are filtered by `SEARCH_DOMAIN_BLOCKLIST`). For a cleaner run use a public-domain portrait of a public figure — reverse search then lands on Wikipedia / museum pages:

```bash
python scripts/fetch_sample.py --name lincoln       # or curie | einstein | tesla
python main.py demo --image samples/lincoln.jpg --image-url <URL printed by the script>
```

---

## Commands

```bash
python main.py identify --image <path> [--image-url URL] [--provider auto|yandex|serpapi|bing|bing_scrape]
                        [--threshold 0.45] [--max-results 10] [--json]
python main.py verify   --record <id|latest|path.json> [--refetch] [--json]
python main.py tamper   --record <id|latest> [--field caption] [--value "..."] [--out <id>]
python main.py demo     --image <path> [--image-url URL] [--refetch] [--field caption]
python main.py list
python main.py deploy   [--rpc http://127.0.0.1:8545] [--private-key 0x...]
python main.py --debug <command> ...      # full tracebacks
```

- `--image-url` — a public URL of the *same* image (e.g. its Wikimedia / GitHub raw link). Reverse-image engines need a URL; without this flag the Yandex provider uploads the file for you (direct upload, then 0x0.st / catbox.moe as fallback).
- `verify --refetch` — re-downloads the matched post image from the web, hashes the *live* bytes, rebuilds the canonical record and checks it on-chain. This proves the content, not just the local file, is unchanged, and reports pHash similarity if it changed.
- `tamper` — writes `<id>-tampered.json` with one canonical field edited (default: caption) so `verify` can show `TAMPERED`.

Exit codes: `0` ok/verified · `2` bad input · `3` pipeline failure · `4` tampered · `5` demo did not produce VERIFIED-then-TAMPERED.

---

## Example run

`python main.py demo --image samples/lincoln.jpg --image-url https://upload.wikimedia.org/.../960px-Abraham_Lincoln_O-77_matte_collodion_print.jpg --refetch`
(Google Lens via SerpAPI, Ganache on `127.0.0.1:8545`)

```
============================================================
 FACE IDENTIFICATION & BLOCKCHAIN VERIFICATION
============================================================

[1/6] Loading input image...
  ✓ Image: samples/lincoln.jpg (276.5 KB)

[2/6] Detecting face...
  ✓ Face 1: bbox=(248,179,633,774) conf=0.89

[3/6] Generating face embedding...
  ✓ ArcFace embedding: dim=512, L2 norm=1.000
  ✓ Perceptual hash (pHash): ecb14eb3b649a384

[4/6] Reverse-image search on the web...
  → Provider: serpapi-lens
  ✓ Search completed — 12 page(s) found; evaluating top 6
     1. [en.wikipedia.org] Abraham Lincoln - Wikipedia — https://en.wikipedia.org/wiki/Abraham_Lincoln
     2. [en.wikipedia.org] Presidency of Abraham Lincoln - Wikipedia — https://en.wikipedia.org/wiki/Presidency_of_Abraham_Lincoln
     3. [www.pinterest.com] 150 Best ABRAHAM LINCOLN presidential portrait ideas ... — https://www.pinterest.com/dangerousdan9317/...
     4. [www.instagram.com] One of the last photographs taken of Abraham Lincoln — https://www.instagram.com/p/DSAvDiKCFsv/
     5. [www.pinterest.com] president.lincoln. — https://www.pinterest.com/caltalcash/president-lincoln/
     6. [www.threads.com] Abraham Lincoln, one of America's greatest presidents — https://www.threads.com/@historyphotographed/...

[5/6] Comparing faces in candidate pages...
     · 1. en.wikipedia.org             similarity=100.0%  ✓ match
     · 2. en.wikipedia.org             similarity= 68.7%  ✓ match
     · 3. www.pinterest.com            similarity= 71.9%  ✓ match
     · 4. www.instagram.com — image not readable (site served a page instead of the image), skipped
     · 5. www.pinterest.com            similarity= 77.9%  ✓ match
     · 6. www.threads.com — download failed, skipped

------------------------------------------------------------
MATCHING CONTENT
------------------------------------------------------------
Platform       : Wikipedia
Title          : Abraham Lincoln - Wikipedia
URL            : https://en.wikipedia.org/wiki/Abraham_Lincoln
Image URL      : https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Abraham_Lincoln_O-77_matte_collodion_print...
Similarity     : 100.00%  (threshold 45%)
Face match     : YES
Image SHA-256  : 6f0d47f184f2a4ffb2e654d83c74205b320038c26f27b31cb28e18613421ea59
------------------------------------------------------------

[6/6] Creating blockchain verification record...
  ✓ Canonical JSON (487 bytes): {"author":"","caption":"","image_sha256":"6f0d47f1…
  ✓ SHA-256 fingerprint: 0x413c6c372717d3d73c602d52b609eb8bd08ba8831a3d03d2d4ab7663ff0f5728
  ✓ Fingerprint anchored on-chain

  Transaction    : 0xfd24739777a8ead36c2be212c8ba23bb8d00e55d25ca373d2a782c000bcdc48d
  Block          : 9
  Block time     : 1788411461
  Contract       : 0x5FbDB2315678afecb367f032d93F642f64180aa3
  Chain          : id=31337 http://127.0.0.1:8545

>>> STEP A — verify the untouched record (expect VERIFIED)

  ✓ Re-downloaded https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Abraham_Lincoln_O-77_m…
  ✓ Live image SHA-256: 6f0d47f184f2a4ffb2e654d83c74205b320038c26f27b31cb28e18613421ea59
RECORDED HASH  : 0x413c6c372717d3d73c602d52b609eb8bd08ba8831a3d03d2d4ab7663ff0f5728
CURRENT HASH   : 0x413c6c372717d3d73c602d52b609eb8bd08ba8831a3d03d2d4ab7663ff0f5728
Chain          : id=31337  contract=0x5FbDB2315678afecb367f032d93F642f64180aa3  mode=on-chain
Current hash on-chain  : True  (stored ts=1788411461)
Original tx            : 0xfd24739777a8ead36c2be212c8ba23bb8d00e55d25ca373d2a782c000bcdc48d  block #9
Live image unchanged   : True  (pHash similarity 100.0%)
============================================================
✓ VERIFIED — fingerprint matches the blockchain record
  No modification detected.
============================================================

>>> STEP B — tamper with one field of the record
✎ 6b08f14e-tampered.json: 'caption' '' → 'TAMPERED'

>>> STEP C — verify the tampered record (expect TAMPERED)
RECORDED HASH  : 0x413c6c372717d3d73c602d52b609eb8bd08ba8831a3d03d2d4ab7663ff0f5728
CURRENT HASH   : 0x5be38b389d9bd693813ae43e5af4a72e9f7d699fb1c07ee7ddb711b1d2dadb71
Current hash on-chain  : False
Recorded hash on-chain : True
============================================================
✗ TAMPERED — fingerprint does not match
  The data hashes differently from when it was recorded — content was modified.
  The recomputed fingerprint is NOT on the blockchain.
  (The original fingerprint is still on-chain — the record file, not the chain, was altered.)
============================================================

SUMMARY
  original : VERIFIED   0x413c6c372717d3d73c602d52b609eb8bd08ba8831a3d03d2d4ab7663ff0f5728
  tampered : TAMPERED   0x5be38b389d9bd693813ae43e5af4a72e9f7d699fb1c07ee7ddb711b1d2dadb71
```

---

## Search providers

| Provider | Type | Key | How |
|----------|------|-----|-----|
| `yandex` (default) | reverse-image | none | Yandex "search by image" results page; the `sites` block lists pages that contain the image. Direct file upload, or `--image-url`. |
| `serpapi` | reverse-image | `SERPAPI_API_KEY` | Google Lens `visual_matches`. Needs a public URL (`--image-url` or temp host). |
| `bing` | reverse-image | `BING_API_KEY` | Azure Bing Visual Search, prefers `PagesIncludingImage`. |
| `bing_scrape` | **text** image search | none | Bing image results for a caption (`BING_SCRAPE_QUERY`). Not reverse-image; opt-in only, never chosen by `auto`. |

`auto` = serpapi if key → bing if key → yandex. All providers return live results only; if a provider is blocked (e.g. Yandex serves a CAPTCHA) the pipeline stops with a clear message rather than substituting canned data. Results whose domain matches `SEARCH_DOMAIN_BLOCKLIST` are dropped before evaluation; `PREFER_SOCIAL=true` evaluates social / wiki hosts first and adds `SOCIAL_BONUS` (default 0.05) to the ranking score of social-media candidates that already pass the face threshold, so a confident Pinterest/Instagram match outranks a marginally higher blog copy. The raw similarity is always what gets printed and recorded.

---

## Blockchain

**Contract** — `contracts/VerificationRegistry.sol` (Solidity 0.8.20, MIT):

```solidity
mapping(bytes32 => uint256) public records;                 // hash → block timestamp
mapping(bytes32 => address) public authors;                 // hash → sender
event RecordStored(bytes32 indexed dataHash, uint256 timestamp, address indexed sender);
function storeRecord(bytes32 dataHash) external;            // reverts on zero / duplicate
function verifyRecord(bytes32) external view returns (bool exists, uint256 timestamp);
function exists(bytes32) external view returns (bool);
```

Only the 32-byte SHA-256 goes on-chain — no image bytes, text, embeddings or PII. The compiled ABI + bytecode are cached in `contracts/VerificationRegistry.json` (regenerated automatically by py-solc-x when the `.sol` changes).

**Chains** — any EVM JSON-RPC works via `RPC_URL`:

| Option | Setup | Persistence |
|--------|-------|-------------|
| **Ganache** (used in the demo) | `npm install && npx ganache --port 8545 --chain.chainId 31337` | while the node runs |
| Anvil / Hardhat | `anvil --port 8545` / `npx hardhat node` | while the node runs |
| Public testnet (Sepolia etc.) | `RPC_URL=https://…` + funded `PRIVATE_KEY` | permanent |
| **eth-tester** (default when `RPC_URL` is empty/unreachable) | nothing | process lifetime |

`identify` deploys the contract automatically if `CONTRACT_ADDRESS` is unset or has no code, and caches the address in `data/blockchain.json`. Re-storing an existing fingerprint reverts on-chain; the pipeline then looks up the original `RecordStored` event and records that transaction instead of a fake one.

With eth-tester the chain is gone when the process exits, so a later `verify` cannot reach the contract; it says so explicitly and falls back to comparing the recomputed hash with the recorded one (`mode=local-only`). `demo` shares one chain connection across identify → verify → tamper → verify, so the on-chain path works even on eth-tester.

---

## What is hashed

```json
{"author":"","caption":"…","image_sha256":"<sha256 of the downloaded post image>",
 "image_url":"https://…","platform":"knockout.chat","post_url":"https://…",
 "published_at":"","title":"…"}
```

`json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)` → UTF-8 → SHA-256. Missing fields are `""`, never omitted, so the hash is reproducible from the same page and image bytes on any machine. The record JSON in `data/records/<id>.json` also stores a pHash of the matched image, the ranked candidate list, the search query URL and the transaction details.

---

## Testing

```bash
python -m pytest -q          # 35 tests, ~2 s, no network, no InsightFace model required
```

| Suite | Covers |
|-------|--------|
| `test_face.py` | invalid input errors, blank image → 0 faces, cosine correctness, largest-face, threshold |
| `test_hashing.py`, `test_canonicalization.py` | deterministic hashing, key-order independence, UTF-8, schema |
| `test_search.py` | provider factory, missing-key errors, **Yandex HTML parser** (offline fixture), tracking-param stripping, CAPTCHA reported not bypassed, no injected results |
| `test_blockchain.py` | store → verify round-trip, tamper, duplicate revert, `RecordStored` event lookup, ephemeral detection (real in-memory EVM) |
| `test_records.py` | tamper copies, listing, `verify_pipeline` in local-only **and** on-chain mode, pHash behaviour |

---

## Project structure

```
VeriTrace/
├── main.py                        CLI (identify · verify · tamper · demo · list · deploy)
├── contracts/
│   ├── VerificationRegistry.sol
│   └── VerificationRegistry.json  compiled ABI + bytecode (auto-generated)
├── scripts/
│   ├── deploy_contract.py
│   └── fetch_sample.py            public-domain demo portraits
├── src/
│   ├── config.py · pipeline.py
│   ├── face/        detector.py · matcher.py
│   ├── search/      base.py · provider.py · yandex_provider.py · serpapi_provider.py · bing_provider.py
│   ├── extraction/  post_extractor.py
│   ├── verification/ canonicalizer.py · hasher.py · phash.py
│   └── blockchain/  client.py
├── tests/                         35 tests
├── samples/input.jpg              OpenCV Lena (demo)
├── data/                          records/, candidates/, blockchain.json (git-ignored)
└── web/                           optional Next.js showcase (see below)
```

**Web showcase** (`web/`, deployed at https://veritrace-dusky.vercel.app) is optional — the task does not require a website. Its `/verify` page runs the *real* reverse-image search (`/api/search` → Yandex) and the same canonical SHA-256 in the browser, but anchors the fingerprint in a clearly-labelled browser ledger (localStorage), because a static page cannot sign transactions to your chain. ArcFace similarity scores exist only in the CLI.

---

## Screen-recording script

3–5 minutes, one terminal, no editing needed:

1. `open samples/input.jpg` (or the Lincoln sample) — show the input face.
2. `npx ganache --port 8545 --chain.chainId 31337` in a second pane — show the chain is live.
3. `python main.py identify --image samples/input.jpg --image-url <url>` — face box, embedding, the live search query URL (open it in a browser to prove it is real), per-candidate similarity, matching post, canonical JSON, SHA-256, tx hash + block.
4. `python main.py verify --record latest --refetch` — live re-download, on-chain lookup, original tx, `✓ VERIFIED`.
5. `python main.py tamper --record latest` then `python main.py verify --record latest-…-tampered` — `✗ TAMPERED`.
6. Optionally show the Ganache log with the two transactions.

Or just: `python main.py demo --image samples/input.jpg --image-url <url> --refetch`.

---

## Known limitations

- **Similarity ≠ identity.** ArcFace cosine ≥ 0.45 means "very likely the same face in these two photos", not a legal identification. The record stores `is_match` and the threshold used.
- **Reverse-image coverage.** Only images that a search engine has indexed can be found. A private photo that appears nowhere online returns 0 results — the pipeline reports that instead of inventing a match.
- **Bot protection.** Yandex may answer with a CAPTCHA under heavy use. VeriTrace never bypasses it; retry later, pass `--image-url`, or switch to `--provider serpapi`.
- **Upload path.** Without `--image-url` the image is uploaded to Yandex (or to 0x0.st / catbox.moe as fallback) — a third party sees the query image. Use `--image-url` if that is a concern.
- **Metadata extraction** is best-effort (`<title>`, OpenGraph, `<meta name=author>`, `article:published_time`); platforms that block anonymous fetches (Instagram, Facebook, 403 pages) yield empty caption/author fields — the hash is still deterministic.
- **eth-tester is ephemeral.** Use Ganache/Anvil (or a testnet) for verification across runs.
- **Metadata drift.** A page can legitimately change its title or caption over time; `verify --refetch` re-hashes the *image* live but keeps the recorded text fields. A text change would need a new `identify` (and a new on-chain record).

## Ethics

Use images you own or that are public and permissively licensed (the bundled sample and `scripts/fetch_sample.py` portraits are). The tool is a proof of concept for content provenance, not a system for identifying private individuals. It respects HTTP status codes (403/429 → skip), never bypasses authentication or CAPTCHAs, and stores nothing on-chain except a hash.

## Contributing

Issues and pull requests are welcome. Before opening a PR:

```bash
python -m pytest -q          # all 35 tests must pass
ruff check . && ruff format --check .
```

## Author

**Vardhan** — [@vardhan23v](https://github.com/vardhan23v)

## License

[MIT](LICENSE) — built for the HH Goa 2026 shortlisting task.
