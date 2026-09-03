"use client";
import { useState } from "react";

const PIPELINE = [
  { n: "01", t: "Face Detection", d: "InsightFace buffalo_l — ArcFace 512-D, 0.80 conf", code: "detector.py" },
  { n: "02", t: "Visual Search", d: "SerpAPI Google Lens / Bing Visual / BingScrape (free)", code: "search/provider.py" },
  { n: "03", t: "Candidate Verify", d: "Download → re-detect → cosine similarity → rank", code: "matcher.py" },
  { n: "04", t: "Canonical + Hash", d: "Sorted JSON → UTF-8 → SHA-256 (32-byte)", code: "canonicalizer.py" },
  { n: "05", t: "Blockchain", d: "VerificationRegistry.sol → storeRecord()", code: "VerificationRegistry.sol" },
  { n: "06", t: "Verify", d: "Recalc hash vs on-chain → VERIFIED / TAMPERED", code: "pipeline.py" },
];

export default function Page() {
  const [active, setActive] = useState(0);
  return (
    <div className="min-h-screen bg-[#08080c] text-zinc-100">
      {/* grid bg */}
      <div className="fixed inset-0 -z-10 bg-[linear-gradient(to_right,#1a1a24_1px,transparent_1px),linear-gradient(to_bottom,#1a1a24_1px,transparent_1px)] bg-[size:48px_48px] opacity-[0.35]" />
      <div className="fixed inset-0 -z-10 bg-gradient-to-b from-transparent via-transparent to-[#08080c]" />

      {/* nav */}
      <nav className="sticky top-0 z-30 backdrop-blur-xl bg-[#08080c]/70 border-b border-white/5">
        <div className="mx-auto max-w-6xl px-5 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-400 grid place-items-center text-black font-black text-xs">V</div>
            <span className="font-semibold tracking-tight">VeriTrace</span>
            <span className="hidden sm:inline text-xs px-2 py-0.5 rounded-full border border-white/10 text-zinc-400">HH Goa 2026 — Task 3</span>
          </div>
          <div className="flex items-center gap-2">
            <a href="https://github.com/vardhan23v/VeriTrace" target="_blank" className="hidden sm:inline-flex text-xs text-zinc-400 hover:text-white px-3 py-1.5 rounded-full border border-white/10">GitHub →</a>
            <a href="#cli" className="text-xs bg-white text-black px-4 py-1.5 rounded-full font-medium hover:bg-zinc-200">Run CLI</a>
          </div>
        </div>
      </nav>

      {/* hero */}
      <section className="mx-auto max-w-6xl px-5 pt-10 pb-8">
        <div className="inline-flex items-center gap-2 text-[11px] tracking-widest uppercase text-emerald-300/80 border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 rounded-full">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> Production PoC • Real Search • Real Chain
        </div>
        <h1 className="mt-4 text-4xl sm:text-5xl font-black tracking-tighter leading-[0.9] max-w-3xl">
          Face identification
          <span className="bg-gradient-to-r from-emerald-300 to-cyan-300 bg-clip-text text-transparent"> → web discovery</span>
          <br />→ blockchain verification.
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-zinc-400">
          Input a face → InsightFace detection + ArcFace embedding → <span className="text-zinc-200">genuine visual search</span> (SerpAPI Lens / Bing) → candidate face-compare →
          canonical JSON → SHA-256 → <span className="text-zinc-200">Solidity VerificationRegistry</span> on eth-tester / Ganache → VERIFIED / TAMPERED.
          No mocks. No hard-coded posts.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          <a href="#cli" className="inline-flex items-center gap-2 bg-emerald-400 text-black text-sm px-4 py-2 rounded-full font-semibold">Start verification <span>→</span></a>
          <a href="https://github.com/vardhan23v/VeriTrace" target="_blank" className="inline-flex items-center gap-2 border border-white/10 text-sm px-4 py-2 rounded-full hover:bg-white/5">View contract on GitHub</a>
          <span className="inline-flex items-center text-xs text-zinc-500 px-2">Python 3.12 • Solidity 0.8.20 • Web3.py • InsightFace</span>
        </div>

        {/* live chain badge */}
        <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { k: "Face conf", v: "0.80", sub: "Lena 208,178→352,390" },
            { k: "Similarity", v: "100.00%", sub: "Face Similarity Match: YES" },
            { k: "Fingerprint", v: "7a63a2…3676", sub: "SHA-256(canonical)" },
            { k: "On-chain", v: "Block #2", sub: "0x5FbDB…aa3 • VERIFIED" },
          ].map((x) => (
            <div key={x.k} className="rounded-2xl border border-white/5 bg-white/[0.04] p-3 backdrop-blur">
              <div className="text-[10px] tracking-widest uppercase text-zinc-500">{x.k}</div>
              <div className="text-sm font-mono font-semibold mt-1">{x.v}</div>
              <div className="text-[11px] text-zinc-500 truncate">{x.sub}</div>
            </div>
          ))}
        </div>
      </section>

      {/* architecture */}
      <section className="mx-auto max-w-6xl px-5 py-8">
        <div className="rounded-[20px] border border-white/5 bg-white/[0.03] overflow-hidden">
          <div className="p-5 sm:p-6 flex flex-col lg:flex-row gap-6">
            <div className="flex-1">
              <h2 className="text-sm font-semibold tracking-tight">Architecture</h2>
              <p className="text-xs text-zinc-500 mt-1">Modular, provider-abstracted, secrets in env. Eth-tester by default, Ganache/Anvil when RPC_URL is set.</p>
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-2">
                {PIPELINE.map((s, i) => (
                  <button
                    key={s.n}
                    onClick={() => setActive(i)}
                    className={`text-left rounded-xl border p-3 transition ${active === i ? "bg-white text-black border-white" : "bg-white/[0.04] border-white/5 hover:bg-white/[0.06] text-zinc-200"}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${active === i ? "bg-black text-white" : "bg-white/10"}`}>{s.n}</span>
                      <span className="text-[10px] font-mono opacity-60">{s.code}</span>
                    </div>
                    <div className="text-xs font-semibold mt-2">{s.t}</div>
                    <div className={`text-[11px] mt-1 leading-4 ${active === i ? "text-zinc-700" : "text-zinc-500"}`}>{s.d}</div>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 rounded-2xl bg-[#0f0f12] border border-white/5 p-4 font-mono text-[11px] leading-4 overflow-auto">
              <div className="text-zinc-500">contracts/VerificationRegistry.sol</div>
              <pre className="mt-2 text-emerald-300/90 whitespace-pre-wrap">{`// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract VerificationRegistry {
  mapping(bytes32 => uint256) public records;
  event RecordStored(bytes32 indexed dataHash,
                     uint256 timestamp,
                     address indexed sender);
  function storeRecord(bytes32 h) external {
    require(h != 0, "invalid");
    require(records[h]==0, "already");
    records[h]=block.timestamp;
    emit RecordStored(h, block.timestamp, msg.sender);
  }
  function verifyRecord(bytes32 h)
    external view returns (bool, uint256) {
    uint256 ts=records[h];
    return (ts!=0, ts);
  }
}`}</pre>
              <div className="mt-4 text-zinc-500">Canonical schema → SHA-256</div>
              <pre className="mt-2 text-cyan-300/90 whitespace-pre-wrap">{`{
  "author": "",
  "caption": "",
  "image_sha256": "7de7ed5…",
  "image_url": "https://…/lena.jpg",
  "platform": "raw.githubusercontent.com",
  "post_url": "https://…/lena.jpg",
  "published_at": "",
  "title": "Image — raw.githubusercontent.com"
}
→ json.dumps(sort_keys, separators=(',',':'))
→ SHA-256 → 0x7a63a215…`}</pre>
            </div>
          </div>
        </div>
      </section>

      {/* CLI */}
      <section id="cli" className="mx-auto max-w-6xl px-5 py-8">
        <h2 className="text-lg font-bold tracking-tight">Run it — CLI first</h2>
        <div className="mt-4 grid lg:grid-cols-2 gap-4">
          <div className="rounded-2xl bg-[#0f0f12] border border-white/5 overflow-hidden">
            <div className="flex items-center gap-1.5 px-4 py-3 border-b border-white/5">
              <span className="h-2.5 w-2.5 rounded-full bg-red-500/80" /><span className="h-2.5 w-2.5 rounded-full bg-yellow-500/80" /><span className="h-2.5 w-2.5 rounded-full bg-green-500/80" />
              <span className="ml-2 text-xs font-mono text-zinc-500">identify → verify → tamper</span>
              <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded bg-emerald-400/15 text-emerald-300 border border-emerald-400/20">real run — Lena</span>
            </div>
            <pre className="p-4 text-[11px] leading-4 font-mono overflow-x-auto text-zinc-300 whitespace-pre-wrap">{`$ python main.py identify --image ./samples/input.jpg

[1/6] Loading input image...   ✓ 89.7 KB
[2/6] Detecting face...        ✓ 1 face bbox=(208,178,352,390) conf=0.80
[3/6] Generating embedding...  ✓ dim=512 L2=1.000
[4/6] Searching the web...     → bing_scrape (free, hits Bing HTML)
                               ✓ 6 candidates
[5/6] Comparing candidates...  · 100.0% — raw.githubusercontent.com ✓
                               — Face Similarity Match: YES
[6/6] Blockchain record...     ✓ SHA-256 7a63a215…3676
                               ✓ tx a4e81b92…809a7e  block 2
                               ✓ contract 0x5FbDB…aa3

→ Record de5d7744  data/records/de5d7744.json

$ python main.py verify --record latest
  ON-CHAIN HASH  0x7a63a215…
  CURRENT HASH   0x7a63a215…
  ✓ VERIFIED — BLOCKCHAIN VERIFICATION SUCCESSFUL

$ # tamper canonical.caption → re-verify
$ python main.py verify --record tampered
  ON-CHAIN 0x7a63a215…  CURRENT 0x102f3ae3…
  ✗ TAMPERED — fingerprint mismatch`}</pre>
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-white/5 bg-white/[0.04] p-4">
              <div className="text-xs font-semibold">Quick start</div>
              <pre className="mt-2 p-3 rounded-xl bg-black/50 border border-white/5 text-[11px] font-mono leading-4 overflow-x-auto whitespace-pre-wrap">{`python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # opencv 4.10.0.84
cp .env.example .env

# persistent chain (optional)
npx ganache --port 8545 --chain.chainId 31337 \\
  --wallet.mnemonic "test test ..." --logging.quiet &
python scripts/deploy_contract.py

python main.py identify --image ./samples/input.jpg
python main.py verify --record latest
python -m pytest -v`}</pre>
              <div className="mt-3 flex gap-2">
                <a href="https://github.com/vardhan23v/VeriTrace" target="_blank" className="text-xs bg-white text-black px-3 py-1.5 rounded-full font-medium">GitHub Repo →</a>
                <a href="https://github.com/vardhan23v/VeriTrace#readme" target="_blank" className="text-xs border border-white/10 px-3 py-1.5 rounded-full">Readme</a>
              </div>
            </div>

            <div className="rounded-2xl border border-white/5 bg-white/[0.04] p-4">
              <div className="text-xs font-semibold">Why this PoC is real</div>
              <ul className="mt-2 space-y-1.5 text-xs leading-5 text-zinc-400 list-disc list-inside">
                <li><span className="text-zinc-200">InsightFace buffalo_l</span> ArcFace — not heuristics</li>
                <li><span className="text-zinc-200">SerpAPI Google Lens</span> when key present; <span className="text-zinc-200">BingScrape</span> free fallback hits Bing HTML (`murl`)</li>
                <li>Candidate images are <span className="text-zinc-200">downloaded over HTTPS</span> and face-verified — not a local DB</li>
                <li>Chain is <span className="text-zinc-200">PyEVM / Ganache</span> — `storeRecord`/`verifyRecord` are real contract calls</li>
                <li>Only <span className="text-zinc-200">SHA-256(canonical)</span> on-chain — no PII</li>
              </ul>
            </div>

            <div className="rounded-2xl border border-emerald-400/15 bg-emerald-400/5 p-4">
              <div className="text-xs font-semibold text-emerald-300">For evaluators</div>
              <p className="text-xs leading-5 text-zinc-400 mt-1">Default works with no keys (bing_scrape). For true reverse-image set <span className="font-mono text-zinc-200">SERPAPI_API_KEY</span> from serpapi.com (100 free). Threshold is configurable — CLI never claims absolute identity, only “Face Similarity Match”.</p>
            </div>
          </div>
        </div>
      </section>

      {/* footer */}
      <footer className="mx-auto max-w-6xl px-5 py-10 border-t border-white/5 mt-4">
        <div className="flex flex-col sm:flex-row justify-between gap-3 text-xs text-zinc-500">
          <span>© VeriTrace — HH Goa 2026 Task 3 • MIT • Python 3.12 • Solidity 0.8.20</span>
          <span className="font-mono">samples/input.jpg — OpenCV Lena (permissive) • not a private individual</span>
        </div>
      </footer>
    </div>
  );
}
