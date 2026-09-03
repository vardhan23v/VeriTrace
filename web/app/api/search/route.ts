import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

/**
 * GET /api/search?image_url=<public image URL>&max=8
 *
 * Genuine reverse-image search, mirroring src/search/yandex_provider.py:
 * fetches the Yandex "search by image" results page server-side and extracts the
 * pages that contain the image from the embedded data-state JSON.
 * No API key. No hardcoded results. Returns [] when nothing is found.
 */

type Result = { title: string; url: string; image_url: string; source: string; thumbnail: string; description?: string };

const TRACKING = new Set(["utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "yclid"]);
const BLOCKLIST = ["porn", "xxx", "sex", "nude", "naked", "adult", "escort"];

function stripTracking(u: string): string {
  try {
    const url = new URL(u);
    for (const k of [...url.searchParams.keys()]) if (TRACKING.has(k)) url.searchParams.delete(k);
    url.hash = "";
    return url.toString();
  } catch {
    return u;
  }
}
const abs = (u: string) => (u.startsWith("//") ? "https:" + u : u);

function decodeEntities(s: string): string {
  return s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
}

function* siteLists(node: any): Generator<any[]> {
  const stack = [node];
  while (stack.length) {
    const n = stack.pop();
    if (Array.isArray(n)) { for (const x of n) if (x && typeof x === "object") stack.push(x); }
    else if (n && typeof n === "object") {
      for (const [k, v] of Object.entries(n)) {
        if (k === "sites" && Array.isArray(v)) yield v;
        else if (v && typeof v === "object") stack.push(v);
      }
    }
  }
}

function parseYandex(html: string, max: number): Result[] {
  const out: Result[] = [];
  const seen = new Set<string>();
  const re = /data-state="([^"]+)"/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    const raw = decodeEntities(m[1]);
    if (!raw.includes("cbirSites") && !raw.includes('"sites"')) continue;
    let state: any;
    try { state = JSON.parse(raw); } catch { continue; }
    for (const sites of siteLists(state)) {
      for (const s of sites) {
        const url = stripTracking(String(s?.url || ""));
        if (!url.startsWith("http") || seen.has(url)) continue;
        const domain = String(s.domain || new URL(url).hostname).toLowerCase();
        if (BLOCKLIST.some((b) => domain.includes(b))) continue;
        seen.add(url);
        const img = abs(String(s?.originalImage?.url || s?.thumb?.url || ""));
        out.push({
          title: String(s.title || `Page on ${domain}`).trim(),
          url,
          image_url: img,
          source: domain,
          thumbnail: abs(String(s?.thumb?.url || "")) || img,
          description: String(s.description || "").trim(),
        });
        if (out.length >= max) return out;
      }
    }
    if (out.length) break;
  }
  return out;
}

export async function GET(req: NextRequest) {
  const imageUrl = req.nextUrl.searchParams.get("image_url");
  const max = Math.min(parseInt(req.nextUrl.searchParams.get("max") || "8", 10) || 8, 30);
  if (!imageUrl || !/^https?:\/\//i.test(imageUrl)) {
    return NextResponse.json({ error: "image_url (public http(s) URL of the query image) is required" }, { status: 400 });
  }

  const yandex = `https://yandex.com/images/search?rpt=imageview&url=${encodeURIComponent(imageUrl)}`;
  try {
    const r = await fetch(yandex, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        Accept: "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
      },
      cache: "no-store",
    });
    const html = await r.text();
    if (!r.ok) return NextResponse.json({ provider: "yandex", query: yandex, results: [], error: `Yandex HTTP ${r.status}` }, { status: 502 });
    if (/showcaptcha|smartcaptcha/i.test(html)) {
      return NextResponse.json({ provider: "yandex", query: yandex, results: [], error: "Yandex served a CAPTCHA (bot protection). Not bypassed — retry later or run the Python CLI." }, { status: 503 });
    }
    const results = parseYandex(html, max);
    return NextResponse.json({ provider: "yandex", query: yandex, results });
  } catch (e: any) {
    return NextResponse.json({ provider: "yandex", query: yandex, results: [], error: e?.message || String(e) }, { status: 502 });
  }
}
