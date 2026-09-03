import Link from "next/link";

export const metadata = {
  title: "About — VeriTrace",
  description: "About VeriTrace — Face Identification → Web Discovery → Blockchain Verification (HH Goa 2026 Task 3)",
};

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-[#08080c] text-zinc-100">
      <div className="fixed inset-0 -z-10 bg-[linear-gradient(to_right,#1a1a24_1px,transparent_1px),linear-gradient(to_bottom,#1a1a24_1px,transparent_1px)] bg-[size:48px_48px] opacity-[0.35]" />
      <div className="fixed inset-0 -z-10 bg-gradient-to-b from-transparent via-transparent to-[#08080c]" />

      <nav className="sticky top-0 z-30 backdrop-blur-xl bg-[#08080c]/70 border-b border-white/5">
        <div className="mx-auto max-w-6xl px-5 h-14 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3">
            <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-emerald-400 to-cyan-400 grid place-items-center text-black font-black text-xs">V</div>
            <span className="font-semibold tracking-tight">VeriTrace</span>
            <span className="hidden sm:inline text-xs px-2 py-0.5 rounded-full border border-white/10 text-zinc-400">HH Goa 2026 — Task 3</span>
          </Link>
          <div className="flex items-center gap-2">
            <Link href="/" className="hidden sm:inline-flex text-xs text-zinc-400 hover:text-white px-3 py-1.5">Home</Link>
            <Link href="/about" className="hidden sm:inline-flex text-xs text-white px-3 py-1.5 rounded-full border border-white/15 bg-white/10">About</Link>
            <a href="https://github.com/vardhan23v/VeriTrace" target="_blank" rel="noopener noreferrer" className="hidden sm:inline-flex text-xs text-zinc-400 hover:text-white px-3 py-1.5 rounded-full border border-white/10">GitHub →</a>
            <Link href="/#cli" className="text-xs bg-white text-black px-4 py-1.5 rounded-full font-medium hover:bg-zinc-200">Run CLI</Link>
          </div>
        </div>
      </nav>

      <main className="mx-auto max-w-3xl px-5 py-10">
        <div className="inline-flex items-center gap-2 text-[11px] tracking-widest uppercase text-emerald-300/80 border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 rounded-full">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" /> About this PoC
        </div>
        <h1 className="mt-4 text-3xl sm:text-4xl font-black tracking-tighter leading-[0.95]">About VeriTrace</h1>
        <p className="mt-3 text-sm leading-6 text-zinc-400">
          A production-quality CLI that chains <span className="text-zinc-100">InsightFace (ArcFace 512-D)</span> face verification,
          <span className="text-zinc-100"> genuine visual search</span> (SerpAPI Google Lens / Bing Visual / free BingScrape),
          deterministic <span className="text-zinc-100">SHA-256(canonical JSON)</span>, and a Solidity{" "}
          <span className="text-zinc-100">VerificationRegistry</span> on an Ethereum-compatible chain (eth-tester / Ganache) into
          a single verifiable pipeline: <span className="text-zinc-200 font-mono text-xs">identify → verify → VERIFIED / TAMPERED</span>.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          <a href="https://veritrace-dusky.vercel.app" className="inline-flex text-xs bg-emerald-400 text-black px-4 py-2 rounded-full font-semibold">Live showcase →</a>
          <a href="https://github.com/vardhan23v/VeriTrace" target="_blank" rel="noopener noreferrer" className="inline-flex text-xs border border-white/10 px-4 py-2 rounded-full hover:bg-white/5">GitHub repo →</a>
          <a href="https://github.com/vardhan23v/VeriTrace#readme" target="_blank" rel="noopener noreferrer" className="inline-flex text-xs border border-white/10 px-4 py-2 rounded-full hover:bg-white/5">README</a>
          <Link href="/" className="inline-flex text-xs text-zinc-400 hover:text-white px-3 py-2">← Back to pipeline</Link>
        </div>

        <div className="mt-8 grid gap-4">
          <section className="rounded-2xl border border-white/5 bg-white/[0.04] p-5">
            <h2 className="text-sm font-semibold">Working links</h2>
            <ul className="mt-3 space-y-2 text-sm">
              <li className="flex items-center justify-between gap-2"><span className="text-zinc-400">Live showcase (Vercel)</span><a href="https://veritrace-dusky.vercel.app" className="font-mono text-xs text-emerald-300 underline decoration-emerald-400/30">https://veritrace-dusky.vercel.app</a></li>
              <li className="flex items-center justify-between gap-2"><span className="text-zinc-400">GitHub repository</span><a href="https://github.com/vardhan23v/VeriTrace" target="_blank" rel="noopener noreferrer" className="font-mono text-xs text-cyan-300 underline decoration-cyan-400/30">https://github.com/vardhan23v/VeriTrace</a></li>
              <li className="flex items-center justify-between gap-2"><span className="text-zinc-400">Contract</span><span className="font-mono text-xs text-zinc-300">contracts/VerificationRegistry.sol</span></li>
              <li className="flex items-center justify-between gap-2"><span className="text-zinc-400">Local pipeline demo</span><span className="font-mono text-xs text-zinc-300">python main.py identify --image ./samples/input.jpg</span></li>
            </ul>
          </section>

          <section className="rounded-2xl border border-white/5 bg-white/[0.04] p-5">
            <h2 className="text-sm font-semibold">Project</h2>
            <p className="mt-2 text-sm leading-6 text-zinc-400">
              Built for <span className="text-zinc-200">HH Goa 2026 Shortlisting — Task 3</span>. No hard-coded posts, no mock search, no fake hashes.
              Candidate images are downloaded over HTTPS and re-verified by face embedding before ranking. Only the 32-byte
              SHA-256 of the canonical record touches the chain — no PII on-chain.
            </p>
            <p className="mt-3 text-xs leading-5 text-zinc-500">
              Default search is <span className="text-zinc-300">bing_scrape</span> (no API key). For true reverse-image, set{" "}
              <span className="font-mono text-zinc-300">SERPAPI_API_KEY</span> from serpapi.com (100 free searches). Threshold is configurable;
              CLI reports “Face Similarity Match”, never absolute identity.
            </p>
          </section>

          <section className="rounded-2xl border border-white/5 bg-white/[0.04] p-5">
            <h2 className="text-sm font-semibold">Stack</h2>
            <p className="mt-2 font-mono text-xs leading-6 text-zinc-400">
              Python 3.12 · InsightFace buffalo_l · OpenCV 4.10.0.84 · onnxruntime · Web3.py 6 · py-solc-x · eth-tester / Ganache · Solidity 0.8.20 · Next.js 15.3.9
            </p>
          </section>

          <section className="rounded-2xl border border-emerald-400/15 bg-emerald-400/5 p-5">
            <h2 className="text-xs font-semibold tracking-widest uppercase text-emerald-300">Author</h2>
            <p className="mt-2 text-sm text-zinc-300">
              <a href="https://github.com/vardhan23v" target="_blank" rel="noopener noreferrer" className="underline decoration-white/20 hover:text-white">vardhan23v</a>
              <span className="text-zinc-500"> — HH Goa 2026. MIT licensed. </span>
              <a href="mailto:vardhan@example.com" className="text-zinc-400 hover:text-white">Contact</a>
            </p>
          </section>
        </div>
      </main>

      <footer className="mx-auto max-w-3xl px-5 py-8 border-t border-white/5 mt-6">
        <div className="flex flex-col sm:flex-row justify-between gap-2 text-xs text-zinc-500">
          <span>© VeriTrace — HH Goa 2026 Task 3 · <a href="https://veritrace-dusky.vercel.app" className="underline decoration-white/15 hover:text-zinc-300">veritrace-dusky.vercel.app</a></span>
          <Link href="/" className="hover:text-zinc-300">Home →</Link>
        </div>
      </footer>
    </div>
  );
}
