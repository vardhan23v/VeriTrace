"""search.serpapi_provider — Google Lens via SerpAPI (genuine reverse-image search, key required).

Docs: https://serpapi.com/search-api/google-lens
Requires ``SERPAPI_API_KEY``. Google Lens needs a *public URL* for the query image, so we
either use the caller-supplied ``image_url`` or host the file temporarily (0x0.st / catbox.moe).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from urllib.parse import urlparse

import requests

from .base import SearchResult, VisualSearchProvider
from .yandex_provider import strip_tracking, upload_to_temp_host

logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


class SerpApiLensProvider(VisualSearchProvider):
    name = "serpapi-lens"

    def __init__(self, api_key: str | None = None, image_url: str | None = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")
        self.image_url = (image_url or os.getenv("INPUT_IMAGE_URL", "")).strip() or None
        if not self.api_key:
            raise ValueError(
                "SERPAPI_API_KEY not set. Get a free key at https://serpapi.com/dashboard "
                "(100 searches/month free) and set SERPAPI_API_KEY in .env, or use --provider yandex (no key)."
            )

    def search(self, image_path: str, max_results: int = 10) -> list[SearchResult]:
        p = Path(image_path)
        if not p.exists():
            raise FileNotFoundError(image_path)

        public_url = self.image_url or upload_to_temp_host(str(p))
        if not public_url:
            raise RuntimeError(
                "Failed to obtain a public URL for the image (0x0.st / catbox.moe unavailable). "
                "Pass --image-url <public-url> or use --provider yandex."
            )

        params = {"engine": "google_lens", "url": public_url, "api_key": self.api_key}
        logger.info("SerpAPI Google Lens search: %s", public_url)
        resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=45)
        if resp.status_code == 401:
            raise RuntimeError("SerpAPI authentication failed — check SERPAPI_API_KEY.")
        if resp.status_code == 429:
            raise RuntimeError("SerpAPI rate limit hit (429). Wait or upgrade plan.")
        resp.raise_for_status()
        data = resp.json()
        if "error" in data and not data.get("visual_matches"):
            raise RuntimeError(f"SerpAPI error: {data['error']}")

        visual_matches = data.get("visual_matches") or data.get("image_results") or []
        results: list[SearchResult] = []
        seen: set[str] = set()
        for item in visual_matches:
            url = strip_tracking(item.get("link") or item.get("url") or "")
            if not url.startswith("http") or url in seen:
                continue
            seen.add(url)
            img = item.get("image") or item.get("original") or item.get("thumbnail")
            source = urlparse(url).netloc or item.get("source") or "unknown"
            results.append(
                SearchResult(
                    title=item.get("title") or item.get("source") or f"Page on {source}",
                    url=url,
                    source=source,
                    image_url=img,
                    thumbnail_url=item.get("thumbnail"),
                    metadata={"provider": "serpapi-lens", "raw": item, "public_url": public_url},
                )
            )
            if len(results) >= max_results:
                break
        if not results:
            logger.warning("SerpAPI returned 0 visual_matches. Raw keys: %s", list(data.keys()))
        return results
