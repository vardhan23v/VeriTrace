import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// Free Bing Image scrape — no API key. Mirrors python bing_provider.py
// Fetches Bing HTML and extracts murl fields. Falls back to permissive demo set.
const DEMO_FALLBACK = [
  {
    title: "Lena — raw.githubusercontent.com (demo fallback)",
    url: "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg",
    image_url: "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg",
    source: "raw.githubusercontent.com",
    thumbnail: "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg",
  },
  {
    title: "Wikimedia Commons — portrait (permissive)",
    url: "https://commons.wikimedia.org/wiki/File:Lena_Soderberg.jpg",
    image_url: "https://upload.wikimedia.org/wikipedia/commons/5/50/Lena_Soderberg.jpg",
    source: "commons.wikimedia.org",
    thumbnail: "https://upload.wikimedia.org/wikipedia/commons/5/50/Lena_Soderberg.jpg",
  },
  {
    title: "Pexels — face portrait (permissive)",
    url: "https://www.pexels.com/photo/woman-in-black-top-774909/",
    image_url: "https://images.pexels.com/photos/774909/pexels-photo-774909.jpeg?auto=compress&cs=tinysrgb&w=600",
    source: "pexels.com",
    thumbnail: "https://images.pexels.com/photos/774909/pexels-photo-774909.jpeg?auto=compress&cs=tinysrgb&w=600",
  },
];

function extractMurls(html: string): string[] {
  const re = /"murl":"([^"]+)"/g;
  const out: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(html))) {
    try {
      out.push(JSON.parse(`"${m[1]}"`));
    } catch {
      out.push(m[1]);
    }
  }
  return [...new Set(out)];
}

export async function GET(req: NextRequest) {
  const q = req.nextUrl.searchParams.get("q") || "portrait face";
  const max = Math.min(parseInt(req.nextUrl.searchParams.get("max") || "6", 10) || 6, 12);

  // Try SerpAPI if configured on Vercel env (server-side only, never exposed)
  const serpKey = process.env.SERPAPI_API_KEY;
  if (serpKey) {
    try {
      // We don't have an actual reverse-image upload from browser here; fall through to Bing scrape
      // Keeping branch for future: if ?image_url= is supplied, call Google Lens.
      const imageUrl = req.nextUrl.searchParams.get("image_url");
      if (imageUrl) {
        const url = `https://serpapi.com/search.json?engine=google_lens&url=${encodeURIComponent(imageUrl)}&api_key=${serpKey}`;
        const r = await fetch(url, { next: { revalidate: 0 } });
        if (r.ok) {
          const j: any = await r.json();
          const visuals: any[] = j.visual_matches || j.image_results || [];
          const mapped = visuals.slice(0, max).map((v: any) => ({
            title: v.title || v.source || "Visual match",
            url: v.link || v.source || v.thumbnail || "",
            image_url: v.thumbnail || v.image || v.link || "",
            source: (() => { try { return new URL(v.link || v.source || "").hostname; } catch { return "serpapi"; } })(),
            thumbnail: v.thumbnail || v.image || "",
          })).filter((x: any) => x.image_url);
          if (mapped.length) return NextResponse.json({ provider: "serpapi", query: q, results: mapped });
        }
      }
    } catch {}
  }

  // Free Bing scrape
  try {
    const bingUrl = `https://www.bing.com/images/search?q=${encodeURIComponent(q)}&form=HDRSC2&first=1`;
    const r = await fetch(bingUrl, {
      headers: {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
      },
      next: { revalidate: 60 },
    });
    if (r.ok) {
      const html = await r.text();
      const murls = extractMurls(html).slice(0, max);
      if (murls.length) {
        const results = murls.map((u) => {
          let host = "bing.com";
          try { host = new URL(u).hostname; } catch {}
          return { title: `Image — ${host}`, url: u, image_url: u, source: host, thumbnail: u };
        });
        return NextResponse.json({ provider: "bing_scrape", query: q, results });
      }
    }
  } catch {}

  return NextResponse.json({ provider: "demo_fallback", query: q, results: DEMO_FALLBACK.slice(0, max), note: "Bing blocked or rate-limited — serving permissive demo images (Wikimedia/Pexels/Lena). Set SERPAPI_API_KEY for true reverse-image." });
}
