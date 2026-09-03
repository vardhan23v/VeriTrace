"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

/**
 * In-browser showcase of the VeriTrace pipeline.
 *
 * What is REAL here:
 *   • face detection on your image (browser FaceDetector API where available)
 *   • reverse-image search — /api/search fetches Yandex "search by image" for the public URL you give
 *   • a face check on each candidate image (FaceDetector, when the CDN allows cross-origin reads)
 *   • canonical JSON + SHA-256 (crypto.subtle) — identical to the Python canonicalizer
 *   • tamper detection by re-hashing
 * What is NOT real here: the blockchain. A browser page cannot sign transactions to your local chain,
 * so the fingerprint is anchored in a *browser ledger* (localStorage) and labelled as such.
 * ArcFace similarity scores are also CLI-only (no 512-D embedding model runs in the page).
 */

const SAMPLE_URL = "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg";

async function sha256Hex(data: ArrayBuffer | string): Promise<string> {
  const buf = typeof data === "string" ? new TextEncoder().encode(data) : data;
  const d = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(d)).map((b) => b.toString(16).padStart(2, "0")).join("");
}
/** Same rules as src/verification/canonicalizer.py: sorted keys, compact separators, UTF-8. */
function canonicalJson(obj: Record<string, string>): string {
  return JSON.stringify(Object.fromEntries(Object.entries(obj).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))));
}
const short = (h: string) => h.slice(0, 10) + "…" + h.slice(-6);

type FaceBox = { x: number; y: number; w: number; h: number };
type Candidate = { title: string; url: string; image_url: string; source: string; thumbnail: string; description?: string; face?: "yes" | "no" | "unknown" };
type Step = { label: string; status: "idle" | "run" | "done" | "err" | "skip"; detail?: string };
type Ledger = Record<string, { canonical: Record<string, string>; anchoredAt: number }>;

const LEDGER_KEY = "veritrace_browser_ledger";
function readLedger(): Ledger { try { return JSON.parse(localStorage.getItem(LEDGER_KEY) || "{}"); } catch { return {}; } }
function writeLedger(l: Ledger) { try { localStorage.setItem(LEDGER_KEY, JSON.stringify(l)); } catch {} }

async function detectFace(img: HTMLImageElement): Promise<FaceBox | null | "unsupported"> {
  const FD: any = (window as any).FaceDetector;
  if (!FD) return "unsupported";
  const cv = document.createElement("canvas");
  cv.width = img.naturalWidth; cv.height = img.naturalHeight;
  cv.getContext("2d")!.drawImage(img, 0, 0);
  const faces: any[] = await new FD({ fastMode: true, maxDetectedFaces: 5 }).detect(cv);
  if (!faces?.length) return null;
  const f = faces.sort((a, b) => b.boundingBox.width * b.boundingBox.height - a.boundingBox.width * a.boundingBox.height)[0].boundingBox;
  return { x: Math.round(f.x), y: Math.round(f.y), w: Math.round(f.width), h: Math.round(f.height) };
}
function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((res, rej) => { const im = new Image(); im.crossOrigin = "anonymous"; im.onload = () => res(im); im.onerror = rej; im.src = src; });
}

const INITIAL_STEPS: Step[] = [
  { label: "Load image", status: "idle" },
  { label: "Detect face", status: "idle" },
  { label: "Reverse-image search", status: "idle" },
  { label: "Face check on candidates", status: "idle" },
  { label: "Canonical + SHA-256", status: "idle" },
  { label: "Anchor (browser ledger)", status: "idle" },
];

export default function VerifyPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [imgNatural, setImgNatural] = useState<{ w: number; h: number } | null>(null);
  const [faceBox, setFaceBox] = useState<FaceBox | null>(null);
  const [detector, setDetector] = useState("Browser FaceDetector");
  const [imageUrl, setImageUrl] = useState(SAMPLE_URL);
  const [steps, setSteps] = useState<Step[]>(INITIAL_STEPS);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [chosen, setChosen] = useState<Candidate | null>(null);
  const [queryUrl, setQueryUrl] = useState<string | null>(null);
  const [imageSha, setImageSha] = useState<string | null>(null);
  const [canonical, setCanonical] = useState<Record<string, string> | null>(null);
  const [hash, setHash] = useState<string | null>(null);
  const [anchoredAt, setAnchoredAt] = useState<number | null>(null);
  const [verifyState, setVerifyState] = useState<"idle" | "verified" | "tampered">("idle");
  const [tamperText, setTamperText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const setStep = (i: number, patch: Partial<Step>) => setSteps((s) => s.map((x, k) => (k === i ? { ...x, ...patch } : x)));

  const reset = () => { setSteps(INITIAL_STEPS); setCandidates([]); setChosen(null); setQueryUrl(null); setCanonical(null); setHash(null); setAnchoredAt(null); setVerifyState("idle"); setErr(null); };

  const handleFile = useCallback(async (f: File) => {
    reset(); setFile(f); setFaceBox(null);
    setPreview(URL.createObjectURL(f));
    setStep(0, { status: "done", detail: `${f.name} · ${(f.size / 1024).toFixed(1)} KB` });
    try { setImageSha(await sha256Hex(await f.arrayBuffer())); } catch { setImageSha(null); }
  }, []);

  useEffect(() => {
    if (!preview || !imgRef.current) return;
    const img = imgRef.current;
    (async () => {
      if (!img.complete) await new Promise<void>((r) => { img.onload = () => r(); img.onerror = () => r(); });
      setImgNatural({ w: img.naturalWidth, h: img.naturalHeight });
      setStep(1, { status: "run" });
      let box: FaceBox | null | "unsupported" = null;
      try { box = await detectFace(img); } catch { box = "unsupported"; }
      if (box === "unsupported") {
        setDetector("FaceDetector API unavailable in this browser");
        setFaceBox(null);
        setStep(1, { status: "skip", detail: "no FaceDetector API — CLI uses InsightFace" });
        return;
      }
      setDetector("Browser FaceDetector (native)");
      setFaceBox(box);
      if (!box) { setStep(1, { status: "err", detail: "no face found" }); setErr("No face detected — try a clearer front-facing portrait."); return; }
      setStep(1, { status: "done", detail: `1 face · (${box.x},${box.y},${box.w}×${box.h})` });
    })();
  }, [preview]);

  async function run() {
    if (!file) { setErr("Choose an image first."); return; }
    if (!/^https?:\/\//.test(imageUrl)) { setErr("Enter a public URL of this image (reverse search needs a URL)."); return; }
    setBusy(true); setErr(null); setVerifyState("idle"); setCanonical(null); setHash(null); setAnchoredAt(null);
    try {
      setStep(2, { status: "run", detail: "Yandex CBIR via /api/search" });
      const r = await fetch(`/api/search?image_url=${encodeURIComponent(imageUrl)}&max=10`, { cache: "no-store" });
      const j = await r.json();
      setQueryUrl(j.query || null);
      if (!r.ok) throw new Error(j.error || `search failed (${r.status})`);
      const results: Candidate[] = j.results || [];
      if (!results.length) throw new Error("No page on the web contains this image (0 results). Try another public image URL.");
      setStep(2, { status: "done", detail: `${results.length} page(s) contain this image` });

      setStep(3, { status: "run", detail: "FaceDetector on each candidate" });
      const checked: Candidate[] = await Promise.all(results.map(async (c) => {
        try {
          const im = await loadImage(c.image_url || c.thumbnail);
          const box = await detectFace(im);
          return { ...c, face: box === "unsupported" ? "unknown" : box ? "yes" : "no" } as Candidate;
        } catch { return { ...c, face: "unknown" } as Candidate; }
      }));
      const withFace = checked.filter((c) => c.face === "yes");
      const pick = withFace[0] || checked[0];
      setCandidates(checked); setChosen(pick);
      setStep(3, { status: "done", detail: `${withFace.length} with a face · ${checked.filter((c) => c.face === "unknown").length} unreadable (CORS)` });

      await fingerprint(pick, "");
    } catch (e: any) {
      setErr(e?.message || String(e));
      setSteps((s) => s.map((x) => (x.status === "run" ? { ...x, status: "err", detail: e?.message } : x)));
    } finally { setBusy(false); }
  }

  async function fingerprint(pick: Candidate, caption: string) {
    setStep(4, { status: "run" });
    const canon: Record<string, string> = {
      author: "", caption: caption || pick.description || "", image_sha256: imageSha || "", image_url: pick.image_url,
      platform: pick.source, post_url: pick.url, published_at: "", title: pick.title,
    };
    const h = await sha256Hex(canonicalJson(canon));
    setCanonical(canon); setHash(h);
    setStep(4, { status: "done", detail: `0x${short(h)}` });
    setStep(5, { status: "run" });
    const ledger = readLedger();
    const at = ledger[h]?.anchoredAt || Date.now();
    ledger[h] = { canonical: canon, anchoredAt: at };
    writeLedger(ledger);
    setAnchoredAt(at); setVerifyState("verified");
    setStep(5, { status: "done", detail: ledger[h] && at !== Date.now() ? "already in ledger" : "stored in localStorage" });
  }

  async function recheck(tampered: boolean) {
    if (!canonical || !hash) return;
    const cur = tampered ? { ...canonical, caption: tamperText || canonical.caption + " [edited]" } : canonical;
    const h = await sha256Hex(canonicalJson(cur));
    setVerifyState(readLedger()[h] ? "verified" : "tampered");
  }

  const onDrop = useCallback((e: React.DragEvent) => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) handleFile(f); }, [handleFile]);

  return (
    <div className="min-h-screen bg-[#FFFBF2] text-[#1A1A18]">
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
              <Link href="/about" className="hidden sm:inline-flex rounded-full px-4 py-2 text-sm font-medium text-[#5A5753] hover:bg-[#F3EEE6]">About</Link>
              <Link href="/verify" className="rounded-full bg-[#1A1A18] px-4 py-2 text-sm font-semibold text-white">Verify</Link>
              <a href="https://github.com/vardhan23v/VeriTrace" target="_blank" rel="noopener noreferrer" className="hidden sm:inline-flex rounded-full border border-[#E8E0D6] px-4 py-2 text-sm font-medium">GitHub</a>
            </div>
          </div>
        </nav>
      </div>

      <main className="mx-auto max-w-[1120px] px-4 sm:px-6 py-8">
        <div className="inline-flex items-center gap-2 rounded-full border border-[#E8E0D6] bg-white px-3 py-1.5 text-xs font-medium text-[#8A817C] shadow-sm">
          <span className="h-2 w-2 rounded-full bg-[#0E7C5A] animate-pulse" /> Browser showcase — real search, real hashing, simulated ledger
        </div>
        <h1 className="display mt-3 text-[32px] sm:text-[38px] font-bold tracking-tight leading-[0.95]">Face → where it appears on the web → fingerprint</h1>
        <p className="mt-2 max-w-[720px] text-sm leading-6 text-[#5A5753]">
          The search step calls Yandex reverse-image search for the public URL you enter, so every candidate below is a page that really contains that image.
          Hashing is the same canonical SHA-256 the CLI anchors on-chain. The blockchain itself is CLI-only — this page keeps the fingerprint in a
          <span className="font-semibold text-[#1A1A18]"> browser ledger</span> so you can still see tamper detection work.
        </p>

        <div className="mt-6 grid lg:grid-cols-[380px_1fr] gap-5">
          <div className="space-y-4">
            <div onDragOver={(e) => e.preventDefault()} onDrop={onDrop} className={`rounded-[24px] border-2 border-dashed bg-white p-4 shadow-sm ${file ? "border-[#0E7C5A]/30" : "border-[#E8E0D6]"}`}>
              <div className="text-sm font-semibold">1 · Drop a portrait</div>
              <p className="mt-1 text-xs leading-5 text-[#8A817C]">Use an image that exists publicly (e.g. a Wikimedia portrait). The bundled sample is OpenCV&apos;s Lena.</p>
              <label className="mt-3 inline-flex cursor-pointer rounded-full bg-[#1A1A18] px-5 py-2.5 text-sm font-semibold text-white hover:bg-black">
                Choose image
                <input type="file" accept="image/*" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
              </label>
              {file && <div className="mt-2 mono text-xs text-[#5A5753]">{file.name} · {(file.size / 1024).toFixed(1)} KB{imageSha ? ` · sha256 ${short(imageSha)}` : ""}</div>}
            </div>

            <div className="rounded-[24px] border border-[#E8E0D6] bg-white p-4 shadow-sm">
              <div className="text-sm font-semibold">2 · Public URL of the same image</div>
              <p className="mt-1 text-xs leading-5 text-[#8A817C]">Reverse-image engines need a URL. The CLI uploads for you; the browser page asks for one instead.</p>
              <input value={imageUrl} onChange={(e) => setImageUrl(e.target.value)} placeholder="https://…/photo.jpg" className="mono mt-2 w-full rounded-2xl border border-[#E8E0D6] bg-[#FFFBF2] px-3 py-2 text-xs" />
              <button onClick={() => setImageUrl(SAMPLE_URL)} className="mt-2 text-xs font-medium text-[#0E7C5A] underline">use sample URL</button>
              {err && <div className="mt-3 rounded-2xl border border-red-200 bg-red-50 px-3 py-2 text-xs font-medium text-red-700">{err}</div>}
            </div>

            <div className="rounded-[24px] border border-[#E8E0D6] bg-white p-3 shadow-sm">
              <div className="flex items-center justify-between"><span className="text-xs font-semibold">Preview</span><span className="mono text-[11px] text-[#8A817C]">{detector}</span></div>
              <div className="mt-3 relative overflow-hidden rounded-[20px] border border-[#E8E0D6] bg-[#FFFBF2] aspect-square grid place-items-center">
                {preview ? (
                  <div className="relative h-full w-full">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img ref={imgRef} src={preview} alt="input" className="h-full w-full object-contain" />
                    {faceBox && imgNatural && (
                      <div className="absolute rounded-[12px] border-[2.5px] border-[#0E7C5A] shadow-[0_0_0_4px_rgba(14,124,90,0.16)] pointer-events-none"
                        style={{ left: `${(faceBox.x / imgNatural.w) * 100}%`, top: `${(faceBox.y / imgNatural.h) * 100}%`, width: `${(faceBox.w / imgNatural.w) * 100}%`, height: `${(faceBox.h / imgNatural.h) * 100}%` }}>
                        <span className="absolute -top-6 left-0 rounded-full bg-[#0E7C5A] px-2 py-0.5 text-[11px] font-bold text-white">face</span>
                      </div>
                    )}
                  </div>
                ) : <span className="text-sm text-[#8A817C]">No image yet</span>}
              </div>
            </div>

            <button onClick={run} disabled={!file || busy}
              className={`w-full rounded-full py-3.5 text-sm font-semibold ${!file || busy ? "bg-[#E8E0D6] text-[#8A817C] cursor-not-allowed" : "bg-[#0E7C5A] text-white hover:bg-[#0A5E45] shadow-[0_8px_20px_rgba(14,124,90,0.25)]"}`}>
              {busy ? "Searching…" : "Run → search + face check + fingerprint"}
            </button>
          </div>

          <div className="space-y-4">
            <div className="rounded-[24px] border border-[#E8E0D6] bg-white p-4 shadow-sm">
              <div className="text-sm font-semibold">Pipeline</div>
              <div className="mt-3 grid grid-cols-2 gap-2.5">
                {steps.map((s, i) => (
                  <div key={i} className={`rounded-[16px] border p-3 ${s.status === "done" ? "border-[#0E7C5A]/20 bg-[#0E7C5A]/5" : s.status === "run" ? "border-[#1A1A18] bg-[#1A1A18] text-white" : s.status === "err" ? "border-red-200 bg-red-50" : "border-[#E8E0D6] bg-[#FFFBF2]"}`}>
                    <div className="flex items-center justify-between">
                      <span className={`mono text-[11px] font-bold px-2 py-0.5 rounded-full ${s.status === "done" ? "bg-[#0E7C5A] text-white" : s.status === "run" ? "bg-white text-[#1A1A18]" : "bg-white border border-[#E8E0D6] text-[#8A817C]"}`}>0{i + 1}</span>
                      <span className={`mono text-[11px] ${s.status === "run" ? "text-white/60" : "text-[#8A817C]"}`}>{s.status}</span>
                    </div>
                    <div className={`mt-2 text-sm font-semibold ${s.status === "run" ? "text-white" : s.status === "done" ? "text-[#0E7C5A]" : "text-[#1A1A18]"}`}>{s.label}</div>
                    {s.detail && <div className={`mono text-[11px] mt-1 truncate ${s.status === "run" ? "text-white/70" : "text-[#8A817C]"}`}>{s.detail}</div>}
                  </div>
                ))}
              </div>
              {queryUrl && <a href={queryUrl} target="_blank" rel="noopener noreferrer" className="mono mt-3 block truncate text-xs text-[#0E7C5A] underline">open the live Yandex query ↗</a>}
            </div>

            {candidates.length > 0 && (
              <div className="rounded-[24px] border border-[#E8E0D6] bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between"><span className="text-sm font-semibold">Pages containing this image</span><span className="text-xs text-[#8A817C]">click to choose the post to fingerprint</span></div>
                <div className="mt-3 grid gap-2">
                  {candidates.map((c, i) => {
                    const active = chosen?.url === c.url;
                    return (
                      <button key={i} onClick={() => { setChosen(c); fingerprint(c, ""); }} className={`flex gap-3 rounded-[16px] border p-2.5 text-left ${active ? "border-[#1A1A18] bg-[#1A1A18] text-white" : "border-[#E8E0D6] bg-[#FFFBF2] hover:bg-white"}`}>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src={c.thumbnail || c.image_url} alt="" className="h-14 w-14 rounded-xl object-cover border border-black/5 bg-white" referrerPolicy="no-referrer" />
                        <div className="min-w-0 flex-1">
                          <div className={`text-sm font-semibold truncate ${active ? "text-white" : "text-[#1A1A18]"}`}>{c.title}</div>
                          <a href={c.url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className={`mono text-xs truncate block underline ${active ? "text-white/70" : "text-[#0E7C5A]"}`}>{c.url}</a>
                          <div className={`mono text-xs mt-1 ${active ? "text-white/80" : "text-[#8A817C]"}`}>{c.source} · face: {c.face === "yes" ? "detected ✓" : c.face === "no" ? "none" : "unknown (CORS / no API)"}</div>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {hash && canonical && (
              <div className="rounded-[24px] border border-[#E8E0D6] bg-[#1A1A18] p-4 shadow-[0_12px_40px_rgba(0,0,0,0.18)]">
                <div className="flex items-center gap-2">
                  <span className="grid h-7 w-7 place-items-center rounded-full bg-[#0E7C5A] text-white text-xs">⬡</span>
                  <span className="text-sm font-semibold text-white">Fingerprint</span>
                  <span className="ml-auto rounded-full bg-white/10 px-2.5 py-1 text-xs font-medium text-white/70">browser ledger · not a blockchain</span>
                </div>
                <div className="mt-4 rounded-2xl bg-white p-4">
                  <div className="text-xs font-semibold tracking-widest text-[#8A817C]">SHA-256 (canonical JSON)</div>
                  <div className="mono mt-2 break-all text-sm font-bold">0x{hash}</div>
                  <details className="mt-2 text-xs text-[#5A5753]"><summary className="cursor-pointer">canonical record</summary><pre className="mono mt-1 whitespace-pre-wrap break-all text-[11px]">{canonicalJson(canonical)}</pre></details>
                  {anchoredAt && <div className="mono mt-2 text-[11px] text-[#8A817C]">anchored in this browser at {new Date(anchoredAt).toISOString()}</div>}
                </div>
                {verifyState !== "idle" && (
                  <div className={`mt-3 rounded-full px-4 py-3 text-sm font-bold text-center ${verifyState === "verified" ? "bg-[#0E7C5A] text-white" : "bg-[#E85D04] text-white"}`}>
                    {verifyState === "verified" ? "✓ VERIFIED — recomputed fingerprint is in the ledger" : "✗ TAMPERED — recomputed fingerprint is not in the ledger"}
                  </div>
                )}
                <div className="mt-4 flex flex-wrap gap-2">
                  <button onClick={() => recheck(false)} className="rounded-full bg-white px-4 py-2 text-sm font-semibold text-[#1A1A18]">Re-check</button>
                  <input value={tamperText} onChange={(e) => setTamperText(e.target.value)} placeholder="edit the caption to simulate tamper…" className="rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm text-white placeholder:text-white/40 w-64" />
                  <button onClick={() => recheck(true)} className="rounded-full border border-white/15 px-4 py-2 text-sm font-medium text-white hover:bg-white/10">Simulate tamper →</button>
                </div>
              </div>
            )}

            <div className="rounded-[24px] border border-[#E8E0D6] bg-white p-4 text-sm leading-6 text-[#8A817C] shadow-sm">
              <span className="font-semibold text-[#1A1A18]">For the real thing</span> — ArcFace similarity scores, the Solidity VerificationRegistry, transaction hashes and on-chain re-verification — run the CLI:
              <span className="mono ml-1 text-xs text-[#1A1A18]">python main.py demo --image samples/input.jpg</span>. Source on <a href="https://github.com/vardhan23v/VeriTrace" target="_blank" rel="noopener noreferrer" className="font-medium text-[#0E7C5A] underline">GitHub</a>.
            </div>
          </div>
        </div>
      </main>

      <footer className="mx-auto max-w-[1120px] px-4 sm:px-6 py-8 border-t border-[#E8E0D6] mt-2">
        <div className="flex flex-col sm:flex-row justify-between gap-2 text-xs text-[#8A817C]">
          <span>© VeriTrace — HH Goa 2026 Task 3 · <Link href="/about" className="underline decoration-[#E8E0D6] hover:text-[#1A1A18]">About</Link></span>
          <span className="mono">demo images are public / permissive · not for identifying private individuals</span>
        </div>
      </footer>
    </div>
  );
}
