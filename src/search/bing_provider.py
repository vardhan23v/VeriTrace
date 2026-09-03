"""search.bing_provider — Bing Visual Search API (key) + Bing image *text* search scrape (no key).

- ``BingVisualSearchProvider``: Azure Bing Visual Search API. Genuine reverse-image. Needs ``BING_API_KEY``.
- ``BingScrapeProvider``: last-resort, keyless. It is a *text* image search (the query is a
  caption you pass or a generic term), **not** reverse-image search — it never uploads the
  input image. It exists only so the rest of the pipeline can be exercised offline-ish; the
  default ``auto`` provider order prefers real reverse-image providers (SerpAPI, Yandex, Bing API).

Nothing in this module injects fixed results: every candidate comes from an HTTP response.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import requests

from .base import SearchResult, VisualSearchProvider

logger = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


# ── Azure Bing Visual Search (real, key required) ───────────


class BingVisualSearchProvider(VisualSearchProvider):
    """Azure Bing Visual Search. Requires BING_API_KEY."""

    name = "bing-visual"
    ENDPOINT = "https://api.bing.microsoft.com/v7.0/images/visualsearch"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("BING_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "BING_API_KEY not set. Create a Bing Search resource at https://portal.azure.com "
                "and set BING_API_KEY in .env, or use the keyless provider: --provider yandex."
            )

    def search(self, image_path: str, max_results: int = 10) -> list[SearchResult]:
        p = Path(image_path)
        if not p.exists():
            raise FileNotFoundError(str(p))
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        knowledge = '{"imageInfo":{"cropArea":{"top":0,"left":0,"bottom":1,"right":1}}}'
        with open(p, "rb") as f:
            files = {"image": (p.name, f, "image/jpeg")}
            resp = requests.post(self.ENDPOINT, headers=headers, files=files, data={"knowledgeRequest": knowledge}, timeout=45)
        if resp.status_code == 401:
            raise RuntimeError("Bing Visual Search authentication failed — check BING_API_KEY.")
        if resp.status_code == 429:
            raise RuntimeError("Bing Visual Search rate limit (429).")
        resp.raise_for_status()
        j = resp.json()

        results: list[SearchResult] = []
        seen: set[str] = set()
        # Prefer "PagesIncludingImage" (pages that contain the image) over "VisualSearch" (similar images).
        ordered_actions = []
        for tag in j.get("tags", []):
            for action in tag.get("actions", []):
                ordered_actions.append(action)
        ordered_actions.sort(key=lambda a: 0 if a.get("actionType") == "PagesIncludingImage" else 1)

        for action in ordered_actions:
            for item in action.get("data", {}).get("value", []):
                url = item.get("hostPageUrl") or item.get("webSearchUrl") or item.get("contentUrl") or ""
                img = item.get("contentUrl") or item.get("thumbnailUrl")
                if not url or url in seen:
                    continue
                seen.add(url)
                source = urlparse(url).netloc or "bing.com"
                results.append(
                    SearchResult(
                        title=item.get("name") or item.get("displayName") or f"Page on {source}",
                        url=url,
                        source=source,
                        image_url=img,
                        thumbnail_url=item.get("thumbnailUrl"),
                        metadata={"provider": "bing-visual", "action": action.get("actionType"), "raw": item},
                    )
                )
                if len(results) >= max_results:
                    return results
        return results


# ── Bing HTML text-search scrape (free, no key, NOT reverse-image) ─────


def _extract_bing_image_urls(html: str, limit: int) -> list[tuple[str, str]]:
    """Return (image_url, page_url) pairs from Bing image-search HTML (murl/purl JSON attrs)."""
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    for block in re.findall(r'm="(\{[^"]*\})"', html):
        block = block.replace("&quot;", '"').replace("\\u002f", "/").replace("\\/", "/")
        murl = re.search(r'"murl":"([^"]+)"', block)
        purl = re.search(r'"purl":"([^"]+)"', block)
        if not murl:
            continue
        img = murl.group(1)
        if not img.startswith("http") or img in seen:
            continue
        seen.add(img)
        pairs.append((img, purl.group(1) if purl else img))
        if len(pairs) >= limit:
            break
    return pairs


class BingScrapeProvider(VisualSearchProvider):
    """Keyless Bing image *text* search. Explicit opt-in (``--provider bing_scrape``).

    Use ``query`` (or ``BING_SCRAPE_QUERY``) to describe the image; without a query the
    search is a generic portrait search and matches will usually be weak — that is expected
    and is reported honestly by the face-similarity step.
    """

    name = "bing_scrape"

    def __init__(self, query: str | None = None):
        self.query = (query or os.getenv("BING_SCRAPE_QUERY", "")).strip() or "portrait photo face"

    def search(self, image_path: str, max_results: int = 10) -> list[SearchResult]:
        p = Path(image_path)
        if not p.exists():
            raise FileNotFoundError(str(p))
        url = f"https://www.bing.com/images/search?q={quote_plus(self.query)}&form=HDRSC2&first=1&count=35"
        headers = {"User-Agent": _UA, "Accept": "text/html,application/xhtml+xml", "Accept-Language": "en-US,en;q=0.9"}
        logger.info("Bing text image search (not reverse-image): %s", url)
        try:
            resp = requests.get(url, headers=headers, timeout=20, allow_redirects=True)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Bing scrape search failed: {exc}") from exc

        pairs = _extract_bing_image_urls(resp.text, max_results * 3)
        if not pairs:
            raise RuntimeError(
                "Bing returned no image results (blocked or empty). Use --provider yandex "
                "(keyless reverse-image) or set SERPAPI_API_KEY."
            )
        results: list[SearchResult] = []
        for img_url, page_url in pairs[:max_results]:
            domain = urlparse(page_url).netloc or urlparse(img_url).netloc or "bing.com"
            results.append(
                SearchResult(
                    title=f"Bing image result — {domain}",
                    url=page_url,
                    source=domain,
                    image_url=img_url,
                    thumbnail_url=img_url,
                    metadata={"provider": "bing_scrape", "query": self.query, "note": "text search, not reverse-image"},
                )
            )
        return results
