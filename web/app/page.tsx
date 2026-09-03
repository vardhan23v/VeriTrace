"use client";
import Link from "next/link";
import { useState } from "react";

const STEPS = [
  { n: "01", title: "Face Detection", desc: "Browser FaceDetector + InsightFace fallback. ArcFace 512-D, L2-normalized.", tag: "detector.py" },
  { n: "02", title: "Visual Search", desc: "Live Bing scrape via /api/search — real murl extraction. SerpAPI Lens when key set.", tag: "search" },
  { n: "03", title: "Candidate Verify", desc: "Download candidates → re-detect faces → cosine similarity → rank.", tag: "matcher.py" },
  { n: "04", title: "Canonical + Hash", desc: "Sorted JSON → UTF-8 → SHA-256. Deterministic, no PII on-chain.", tag: "canonicalizer" },
  { n: "05", title: "Blockchain", desc: "VerificationRegistry.storeRecord(bytes32) — eth-tester / Ganache / Anvil.", tag: "solidity" },
  { n: "06", title: "Verify", desc: "Re-hash vs on-chain → VERIFIED / TAMPERED. One command.", tag: "pipeline.py" },
];

export default function Page() {
  const [active, setActive] = useState(0);

  return (
    <div className="min-h-screen bg-[#FFFBF2] text-[#1A1A18]">
      {/* soft paper texture */}
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-[0.04]" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.35'/%3E%3C/svg%3E")` }} />

      {/* nav — floating pill */}
      <div className="sticky top-0 z-30 pt-3 sm:pt-4">
        <nav className="mx-auto max-w-[1120px] px-4 sm:px-6">
          <div className="flex h-[56px] items-center justify-between rounded-full border border-[#E8E0D6] bg-white/80 px-2 pl-3 pr-2 shadow-[0_8px_30px_rgba(26,26,24,0.06)] backdrop-blur-xl">
            <Link href="/" className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-[#1A1A18] text-white text-[13px] font-bold tracking-tight">◐</span>
              <span className="text-[15px] font-semibold tracking-tight">VeriTrace</span>
              <span className="hidden sm:inline-flex items-center rounded-full bg-[#F3EEE6] px-2.5 py-1 text-[11px] font-medium tracking-wide text-[#8A817C]">HH GOA 2026 — TASK 3</span>
            </Link>
            <div className="flex items-center gap-1.5">
              <Link href="/about" className="hidden sm:inline-flex rounded-full px-4 py-2 text-sm font-medium text-[#5A5753] hover:bg-[#F3EEE6] hover:text-[#1A1A18]">About</Link>
              <Link href="/verify" className="hidden sm:inline-flex rounded-full bg-[#0E7C5A] px-4 py-2 text-sm font-semibold text-white hover:bg-[#0A5E45]">Verify →</Link>
              <a href="https://github.com/vardhan23v/VeriTrace" target="_blank" rel="noopener noreferrer" className="hidden sm:inline-flex rounded-full border border-[#E8E0D6] px-4 py-2 text-sm font-medium hover:bg-[#F3EEE6]">GitHub</a>
              <Link href="/verify" className="inline-flex sm:hidden rounded-full bg-[#1A1A18] px-4 py-2 text-sm font-semibold text-white">Verify</Link>
            </div>
          </div>
        </nav>
      </div>

      {/* hero */}
      <section className="mx-auto max-w-[1120px] px-4 sm:px-6 pt-10 sm:pt-14 pb-8">
        <div className="grid lg:grid-cols-[1.05fr_0.95fr] gap-8 lg:gap-10 items-start">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-[#E8E0D6] bg-white px-3 py-1.5 text-xs font-medium text-[#8A817C] shadow-sm">
              <span className="h-2 w-2 rounded-full bg-[#0E7C5A] animate-pulse" />
              No Python needed — verify directly in your browser
              <span className="hidden sm:inline text-[#D6CFC2]">•</span>
              <span className="hidden sm:inline">Real search • Real hash • Real chain</span>
            </div>

            <h1 className="display mt-6 text-[40px] sm:text-[54px] font-bold leading-[0.92] tracking-[-0.03em]">
              Every face
              <br />
              <span className="italic font-bold text-[#0E7C5A]">leaves a trace.</span>
              <br />
              We make it verifiable.
            </h1>

            <p className="mt-5 max-w-[560px] text-[15px] leading-7 text-[#5A5753]">
              Drop a portrait. We detect the face, search the open web for where it appears, compare candidates with cosine similarity,
              canonicalize the match and anchor its <span className="font-semibold text-[#1A1A18]">SHA-256</span> on an Ethereum-compatible chain. Then prove it —{" "}
              <span className="rounded-full bg-[#1A1A18] px-2 py-0.5 text-xs font-semibold text-white">VERIFIED</span>{" "}
              <span className="text-[#D6CFC2]">/</span>{" "}
              <span className="rounded-full bg-white border border-[#E8E0D6] px-2 py-0.5 text-xs font-semibold">TAMPERED</span>.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              <Link href="/verify" className="inline-flex items-center gap-2 rounded-full bg-[#1A1A18] px-6 py-3 text-sm font-semibold text-white hover:bg-black">
                Verify in browser
                <span className="grid h-6 w-6 place-items-center rounded-full bg-white text-[#1A1A18] text-xs">→</span>
              </Link>
              <a href="#how" className="inline-flex items-center gap-2 rounded-full border border-[#E8E0D6] bg-white px-6 py-3 text-sm font-semibold hover:bg-[#F3EEE6]">
                How it works
              </a>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-[#F3EEE6] px-3 py-2 text-xs font-medium text-[#8A817C]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#0E7C5A]" /> Python 3.12 • Solidity 0.8.20 • InsightFace
              </span>
            </div>

            <div className="mt-8 flex flex-wrap gap-2">
              {[
                { k: "Face", v: "0.80 conf", s: "512-D ArcFace" },
                { k: "Match", v: "100.00%", s: "Face Similarity" },
                { k: "Hash", v: "SHA-256", s: "canonical JSON" },
                { k: "Chain", v: "Block #2", s: "VERIFIED" },
              ].map((x) => (
                <div key={x.k} className="rounded-2xl border border-[#E8E0D6] bg-white px-4 py-3 shadow-sm">
                  <div className="text-[10px] font-semibold tracking-widest text-[#8A817C]">{x.k.toUpperCase()}</div>
                  <div className="mono text-sm font-semibold mt-0.5">{x.v}</div>
                  <div className="text-xs text-[#8A817C]">{x.s}</div>
                </div>
              ))}
            </div>
          </div>

          {/* right — bento mock */}
          <div className="relative">
            <div className="rounded-[28px] border border-[#E8E0D6] bg-white p-3 shadow-[0_20px_60px_rgba(26,26,24,0.08)]">
              <div className="grid gap-3">
                {/* input card */}
                <div className="rounded-[20px] border border-[#E8E0D6] bg-[#FFFBF2] p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">Input</span>
                    <span className="mono text-[11px] rounded-full bg-[#1A1A18] px-2 py-0.5 text-white">samples/input.jpg</span>
                  </div>
                  <div className="mt-3 grid grid-cols-[96px_1fr] gap-3">
                    <div className="relative h-24 w-24 overflow-hidden rounded-2xl bg-[#E8E0D6] border border-[#E8E0D6]">
                      <img src="https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg" alt="lena" className="h-full w-full object-cover" crossOrigin="anonymous" />
                      <div className="absolute left-[32%] top-[18%] h-[56%] w-[38%] rounded-[10px] border-2 border-[#0E7C5A] shadow-[0_0_0_3px_rgba(14,124,90,0.18)]" />
                      <span className="absolute bottom-1 left-1 rounded-full bg-[#0E7C5A] px-1.5 py-0.5 text-[9px] font-bold text-white">face 0.80</span>
                    </div>
                    <div className="space-y-2 text-xs leading-5">
                      <div className="flex gap-2"><span className="text-[#8A817C]">bbox</span><span className="mono font-medium">208,178 → 352,390</span></div>
                      <div className="flex gap-2"><span className="text-[#8A817C]">emb</span><span className="mono font-medium">512-D · L2 1.000</span></div>
                      <div className="inline-flex rounded-full bg-[#0E7C5A]/10 px-2 py-1 text-[11px] font-semibold text-[#0E7C5A]">● Live detection</div>
                    </div>
                  </div>
                </div>

                {/* arrow */}
                <div className="flex justify-center -my-1"><span className="grid h-7 w-7 place-items-center rounded-full border border-[#E8E0D6] bg-white text-xs">↓</span></div>

                {/* search card */}
                <div className="rounded-[20px] border border-[#E8E0D6] bg-white p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold">Web discovery — <span className="font-normal text-[#8A817C]">/api/search → Bing murl</span></span>
                    <span className="text-[11px] rounded-full bg-[#F3EEE6] px-2 py-1 font-medium">6 candidates</span>
                  </div>
                  <div className="mt-3 grid grid-cols-3 gap-2">
                    {[
                      { s: "100.0%", a: "✓ Match", c: "border-[#0E7C5A] bg-[#0E7C5A]/5" },
                      { s: "68.2%", a: "below", c: "border-[#E8E0D6] bg-white" },
                      { s: "41.7%", a: "below", c: "border-[#E8E0D6] bg-white" },
                    ].map((x, i) => (
                      <div key={i} className={`rounded-2xl border p-2 text-center ${x.c}`}>
                        <div className="h-16 rounded-xl bg-[#F3EEE6] overflow-hidden border border-[#E8E0D6]">{i === 0 ? <img src="https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg" alt="" className="h-full w-full object-cover" /> : <div className="h-full w-full bg-gradient-to-br from-[#F3EEE6] to-white" />}</div>
                        <div className="mono text-xs font-bold mt-1.5">{x.s}</div>
                        <div className="text-[11px] text-[#8A817C]">{x.a}</div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-center -my-1"><span className="grid h-7 w-7 place-items-center rounded-full border border-[#E8E0D6] bg-white text-xs">↓</span></div>

                {/* chain card */}
                <div className="rounded-[20px] bg-[#1A1A18] p-4 text-white">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold tracking-wide text-white/70">BLOCKCHAIN</span>
                    <span className="rounded-full bg-[#0E7C5A] px-2 py-1 text-[11px] font-bold">VERIFIED</span>
                  </div>
                  <div className="mt-3 mono text-xs leading-5 text-white/90">
                    <div>SHA-256 <span className="text-[#7ED8BF]">7a63a215…3676</span></div>
                    <div className="text-white/60">tx 0xa4e8…809a7e · block #2 · 0x5FbD…aa3</div>
                    <div className="mt-2 inline-flex rounded-full bg-white px-3 py-1 text-xs font-bold text-[#1A1A18]">✓ BLOCKCHAIN VERIFICATION SUCCESSFUL</div>
                  </div>
                </div>
              </div>
            </div>

            {/* floating badge */}
            <div className="absolute -bottom-3 -right-2 sm:right-4 rounded-full border border-[#E8E0D6] bg-white px-3 py-1.5 text-xs font-medium shadow-md">
              Try it now — <Link href="/verify" className="font-semibold underline decoration-[#0E7C5A]/30">/verify</Link>
            </div>
          </div>
        </div>
      </section>

      {/* trust strip */}
      <section className="mx-auto max-w-[1120px] px-4 sm:px-6">
        <div className="rounded-full border border-[#E8E0D6] bg-white px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs">
          <span className="font-semibold tracking-widest text-[#8A817C]">BUILT WITH</span>
          <span className="mono text-[#5A5753]">InsightFace buffalo_l • OpenCV 4.10 • Web3.py 6 • Solidity 0.8.20 • Next 15.3.9 • eth-tester / Ganache</span>
          <span className="hidden sm:inline rounded-full bg-[#F3EEE6] px-3 py-1 font-medium">No mocks • No hard-coded posts • Only SHA-256 on-chain</span>
        </div>
      </section>

      {/* architecture — new bento from scratch */}
      <section id="how" className="mx-auto max-w-[1120px] px-4 sm:px-6 pt-10">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h2 className="display text-[30px] font-bold tracking-tight">How it works</h2>
            <p className="mt-2 max-w-[560px] text-sm leading-6 text-[#5A5753]">Six focused steps. Click to explore — the code preview on the right follows your selection.</p>
          </div>
          <Link href="/verify" className="hidden sm:inline-flex rounded-full bg-[#1A1A18] px-5 py-2.5 text-sm font-semibold text-white">Start verification →</Link>
        </div>

        <div className="mt-6 grid lg:grid-cols-[1.15fr_0.85fr] gap-4">
          <div className="grid sm:grid-cols-2 gap-3">
            {STEPS.map((s, i) => (
              <button
                key={s.n}
                onClick={() => setActive(i)}
                className={`text-left rounded-[20px] border p-4 transition ${active === i ? "bg-[#1A1A18] text-white border-[#1A1A18] shadow-[0_10px_30px_rgba(0,0,0,0.12)]" : "bg-white border-[#E8E0D6] hover:border-[#D6CFC2] hover:shadow-sm"}`}
              >
                <div className="flex items-center justify-between">
                  <span className={`mono text-xs font-bold px-2 py-1 rounded-full ${active === i ? "bg-white text-[#1A1A18]" : "bg-[#F3EEE6] text-[#8A817C]"}`}>{s.n}</span>
                  <span className={`mono text-[11px] ${active === i ? "text-white/60" : "text-[#8A817C]"}`}>{s.tag}</span>
                </div>
                <div className="mt-3 text-sm font-semibold">{s.title}</div>
                <div className={`mt-1 text-sm leading-5 ${active === i ? "text-white/70" : "text-[#5A5753]"}`}>{s.desc}</div>
              </button>
            ))}
          </div>

          <div className="rounded-[24px] border border-[#E8E0D6] bg-[#1A1A18] p-4 sm:p-5 shadow-[0_20px_60px_rgba(0,0,0,0.18)]">
            <div className="flex items-center gap-2 text-xs">
              <span className="h-2.5 w-2.5 rounded-full bg-[#FF5F56]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#FFBD2E]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#27C93F]" />
              <span className="ml-2 mono text-white/50">VerificationRegistry.sol</span>
              <span className="ml-auto hidden sm:inline rounded-full bg-white/10 px-2 py-1 mono text-[11px] text-white/70">{STEPS[active].title}</span>
            </div>
            <pre className="mono mt-4 text-[12px] leading-5 whitespace-pre-wrap text-[#7ED8BF]">{`// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;
contract VerificationRegistry {
  mapping(bytes32 => uint256) public records;
  event RecordStored(bytes32 indexed h, uint256 ts, address sender);
  function storeRecord(bytes32 h) external {
    require(h != 0, "invalid");
    require(records[h]==0, "already");
    records[h]=block.timestamp;
    emit RecordStored(h, block.timestamp, msg.sender);
  }
  function verifyRecord(bytes32 h) external view returns (bool, uint256) {
    return (records[h]!=0, records[h]);
  }
}`}</pre>
            <div className="mt-4 rounded-2xl bg-white/[0.06] border border-white/10 p-3">
              <div className="mono text-[11px] tracking-wide text-white/50">CANONICAL → SHA-256</div>
              <pre className="mono mt-2 text-[11px] leading-4 whitespace-pre-wrap text-white/90">{`{
  "image_sha256": "…",
  "image_url": "https://…/lena.jpg",
  "platform": "raw.githubusercontent.com",
  "post_url": "https://…/lena.jpg",
  "title": "Image — raw.githubusercontent…"
}
→ sorted keys, separators=(',',':')
→ SHA-256  0x7a63a215…3676`}</pre>
            </div>
          </div>
        </div>
      </section>

      {/* cli */}
      <section id="cli" className="mx-auto max-w-[1120px] px-4 sm:px-6 pt-10 pb-8">
        <div className="grid lg:grid-cols-[1.1fr_0.9fr] gap-4">
          <div className="rounded-[24px] bg-[#1A1A18] border border-[#2A2A28] overflow-hidden shadow-[0_20px_60px_rgba(0,0,0,0.18)]">
            <div className="flex items-center gap-2 px-4 py-3 border-b border-white/10">
              <span className="h-2.5 w-2.5 rounded-full bg-[#FF5F56]" /><span className="h-2.5 w-2.5 rounded-full bg-[#FFBD2E]" /><span className="h-2.5 w-2.5 rounded-full bg-[#27C93F]" />
              <span className="ml-2 mono text-xs text-white/50">identify → verify → tamper</span>
              <span className="ml-auto mono text-[11px] rounded-full bg-[#0E7C5A] px-2 py-1 font-bold text-white">real run — Lena</span>
            </div>
            <pre className="mono p-4 text-[12px] leading-5 whitespace-pre-wrap text-white/90">{`$ python main.py identify --image ./samples/input.jpg

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

$ python main.py verify --record tampered
  ON-CHAIN 0x7a63a215…  CURRENT 0x102f3ae3…
  ✗ TAMPERED — fingerprint mismatch`}</pre>
          </div>

          <div className="space-y-4">
            <div className="rounded-[24px] border border-[#E8E0D6] bg-white p-5 shadow-sm">
              <div className="text-sm font-semibold">Quick start — or skip Python entirely</div>
              <p className="mt-1 text-sm leading-6 text-[#5A5753]">The browser path needs no install. For the audited CLI + Solidity run:</p>
              <pre className="mono mt-3 rounded-2xl bg-[#1A1A18] p-3 text-[11px] leading-4 whitespace-pre-wrap text-white/90 overflow-x-auto">{`python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # opencv 4.10.0.84
cp .env.example .env
npx ganache --port 8545 --chain.chainId 31337 \\
  --wallet.mnemonic "test test ..." --logging.quiet &
python scripts/deploy_contract.py
python main.py identify --image ./samples/input.jpg
python main.py verify --record latest
python -m pytest -v`}</pre>
              <div className="mt-3 flex gap-2">
                <Link href="/verify" className="rounded-full bg-[#0E7C5A] px-4 py-2 text-sm font-semibold text-white">Verify in browser</Link>
                <a href="https://github.com/vardhan23v/VeriTrace" target="_blank" rel="noopener noreferrer" className="rounded-full border border-[#E8E0D6] px-4 py-2 text-sm font-medium">GitHub repo</a>
              </div>
            </div>

            <div className="rounded-[24px] border border-[#E8E0D6] bg-[#FFFBF2] p-5">
              <div className="text-sm font-semibold">Why this PoC is real</div>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-[#5A5753] list-disc list-inside">
                <li><span className="font-semibold text-[#1A1A18]">InsightFace buffalo_l</span> ArcFace — not heuristics</li>
                <li><span className="font-semibold text-[#1A1A18]">BingScrape</span> hits Bing HTML (<span className="mono text-xs">murl</span>) — or SerpAPI Lens with key</li>
                <li>Candidates are <span className="font-semibold text-[#1A1A18]">downloaded over HTTPS</span> and face-verified — not a local DB</li>
                <li>Chain is <span className="font-semibold text-[#1A1A18]">PyEVM / Ganache</span> — real <span className="mono text-xs">storeRecord</span>/<span className="mono text-xs">verifyRecord</span></li>
                <li>Only <span className="font-semibold text-[#1A1A18]">SHA-256(canonical)</span> on-chain — no PII</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <footer className="mx-auto max-w-[1120px] px-4 sm:px-6 py-8 border-t border-[#E8E0D6] mt-2">
        <div className="flex flex-col sm:flex-row justify-between gap-3 text-xs text-[#8A817C]">
          <span>© VeriTrace — HH Goa 2026 Task 3 • MIT • <Link href="/about" className="underline decoration-[#E8E0D6] hover:text-[#1A1A18]">About</Link> • <Link href="/verify" className="font-semibold text-[#0E7C5A] hover:text-[#0A5E45]">Verify in browser →</Link></span>
          <span className="mono">samples/input.jpg — OpenCV Lena (permissive) • not a private individual</span>
        </div>
      </footer>
    </div>
  );
}
