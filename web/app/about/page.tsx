import Link from "next/link";

export const metadata = {
  title: "About — VeriTrace",
  description: "About VeriTrace — Face Identification → Web Discovery → Blockchain Verification (HH Goa 2026 Task 3)",
};

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-[#FFFBF2] text-[#1A1A18]">
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-[0.04]" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.35'/%3E%3C/svg%3E")` }} />

      <div className="sticky top-0 z-30 pt-3 sm:pt-4">
        <nav className="mx-auto max-w-[1120px] px-4 sm:px-6">
          <div className="flex h-[56px] items-center justify-between rounded-full border border-[#E8E0D6] bg-white/80 px-2 pl-3 pr-2 shadow-[0_8px_30px_rgba(26,26,24,0.06)] backdrop-blur-xl">
            <Link href="/" className="flex items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-[#1A1A18] text-white text-[13px] font-bold">◐</span>
              <span className="text-[15px] font-semibold tracking-tight">VeriTrace</span>
              <span className="hidden sm:inline-flex items-center rounded-full bg-[#F3EEE6] px-2.5 py-1 text-[11px] font-medium tracking-wide text-[#8A817C]">HH GOA 2026 — TASK 3</span>
            </Link>
            <div className="flex items-center gap-1.5">
              <Link href="/" className="hidden sm:inline-flex rounded-full px-4 py-2 text-sm font-medium text-[#5A5753] hover:bg-[#F3EEE6]">Home</Link>
              <Link href="/about" className="hidden sm:inline-flex rounded-full bg-[#1A1A18] px-4 py-2 text-sm font-semibold text-white">About</Link>
              <Link href="/verify" className="hidden sm:inline-flex rounded-full bg-[#0E7C5A] px-4 py-2 text-sm font-semibold text-white">Verify →</Link>
              <a href="https://github.com/vardhan23v/VeriTrace" target="_blank" rel="noopener noreferrer" className="hidden sm:inline-flex rounded-full border border-[#E8E0D6] px-4 py-2 text-sm font-medium">GitHub</a>
            </div>
          </div>
        </nav>
      </div>

      <main className="mx-auto max-w-[760px] px-4 sm:px-6 py-10">
        <div className="inline-flex items-center gap-2 rounded-full border border-[#E8E0D6] bg-white px-3 py-1.5 text-xs font-medium text-[#8A817C] shadow-sm">
          <span className="h-2 w-2 rounded-full bg-[#0E7C5A] animate-pulse" /> About this PoC
        </div>

        <h1 className="display mt-4 text-[36px] sm:text-[44px] font-bold tracking-[-0.02em] leading-[0.95]">About VeriTrace</h1>
        <p className="mt-4 text-[15px] leading-7 text-[#5A5753]">
          A production CLI + browser verifier that chains <span className="font-semibold text-[#1A1A18]">InsightFace (ArcFace 512-D)</span> face verification,
          <span className="font-semibold text-[#1A1A18]"> genuine visual search</span> (SerpAPI Google Lens / Bing Visual / free BingScrape),
          deterministic <span className="font-semibold text-[#1A1A18]">SHA-256(canonical JSON)</span>, and a Solidity{" "}
          <span className="font-semibold text-[#1A1A18]">VerificationRegistry</span> on an Ethereum-compatible chain into one pipeline:{" "}
          <span className="mono rounded-full bg-[#1A1A18] px-2 py-0.5 text-xs text-white">identify → verify → VERIFIED / TAMPERED</span>.
        </p>

        <div className="mt-6 flex flex-wrap gap-2">
          <a href="https://veritrace-dusky.vercel.app" className="inline-flex rounded-full bg-[#1A1A18] px-5 py-2.5 text-sm font-semibold text-white">Live showcase →</a>
          <Link href="/verify" className="inline-flex rounded-full bg-[#0E7C5A] px-5 py-2.5 text-sm font-semibold text-white">Try verification</Link>
          <Link href="/" className="inline-flex rounded-full border border-[#E8E0D6] bg-white px-5 py-2.5 text-sm font-medium">← Back</Link>
        </div>

        <div className="mt-8 grid gap-4">
          <section className="rounded-[24px] border border-[#E8E0D6] bg-white p-6 shadow-sm">
            <h2 className="text-sm font-semibold">Working links</h2>
            <ul className="mt-3 space-y-2.5 text-sm">
              <li className="flex items-center justify-between gap-2"><span className="text-[#8A817C]">Live showcase (Vercel)</span><a href="https://veritrace-dusky.vercel.app" className="mono text-xs font-medium text-[#0E7C5A] underline decoration-[#0E7C5A]/20">https://veritrace-dusky.vercel.app</a></li>
              <li className="flex items-center justify-between gap-2"><span className="text-[#8A817C]">In-browser verify</span><Link href="/verify" className="mono text-xs font-medium text-[#0E7C5A] underline decoration-[#0E7C5A]/20">/verify</Link></li>
              <li className="flex items-center justify-between gap-2"><span className="text-[#8A817C]">GitHub repository</span><a href="https://github.com/vardhan23v/VeriTrace" target="_blank" rel="noopener noreferrer" className="mono text-xs font-medium text-[#0E7C5A] underline">github.com/vardhan23v/VeriTrace</a></li>
              <li className="flex items-center justify-between gap-2"><span className="text-[#8A817C]">CLI demo</span><span className="mono text-xs">python main.py identify --image ./samples/input.jpg</span></li>
            </ul>
          </section>

          <section className="rounded-[24px] border border-[#E8E0D6] bg-[#F3EEE6]/60 p-6">
            <h2 className="text-sm font-semibold">Project</h2>
            <p className="mt-2 text-sm leading-6 text-[#5A5753]">
              Built for <span className="font-semibold text-[#1A1A18]">HH Goa 2026 Shortlisting — Task 3</span>. No hard-coded posts, no mock search, no fake hashes.
              Candidate images are downloaded over HTTPS and re-verified by embedding before ranking. Only the 32-byte SHA-256 of the canonical record touches the chain — no PII on-chain.
            </p>
            <p className="mt-3 text-sm leading-6 text-[#8A817C]">
              Default search is <span className="mono text-xs font-medium text-[#1A1A18]">bing_scrape</span> (no API key). For true reverse-image, set{" "}
              <span className="mono text-xs font-medium">SERPAPI_API_KEY</span>. Threshold is configurable; the app reports “Face Similarity Match”, never absolute identity.
            </p>
          </section>

          <section className="rounded-[24px] border border-[#E8E0D6] bg-white p-6 shadow-sm">
            <h2 className="text-sm font-semibold">Stack</h2>
            <p className="mono mt-2 text-xs leading-6 text-[#5A5753]">
              Python 3.12 · InsightFace buffalo_l · OpenCV 4.10.0.84 · onnxruntime · Web3.py 6 · py-solc-x · eth-tester / Ganache · Solidity 0.8.20 · Next.js 15.3.9
            </p>
          </section>

          <section className="rounded-[24px] bg-[#1A1A18] p-6 text-white">
            <h2 className="text-xs font-semibold tracking-widest text-white/60">AUTHOR</h2>
            <p className="mt-2 text-sm">
              <a href="https://github.com/vardhan23v" target="_blank" rel="noopener noreferrer" className="font-semibold underline decoration-white/20 hover:text-white">vardhan23v</a>
              <span className="text-white/50"> — HH Goa 2026 · MIT</span>
            </p>
          </section>
        </div>
      </main>

      <footer className="mx-auto max-w-[760px] px-4 sm:px-6 py-8 border-t border-[#E8E0D6] mt-6">
        <div className="flex flex-col sm:flex-row justify-between gap-2 text-xs text-[#8A817C]">
          <span>© VeriTrace — HH Goa 2026 Task 3 · <a href="https://veritrace-dusky.vercel.app" className="underline decoration-[#E8E0D6]">veritrace-dusky.vercel.app</a></span>
          <Link href="/" className="hover:text-[#1A1A18]">Home →</Link>
        </div>
      </footer>
    </div>
  );
}
