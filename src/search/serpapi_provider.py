"""search.serpapi_provider — Google Lens via SerpAPI (real visual search).

Docs: https://serpapi.com/search-api/google-lens
Requires: SERPAPI_API_KEY env var.
Uploads image to SerpAPI's temporary hosting via local file (SerpAPI accepts url; we host via base64 or upload).
SerpAPI Google Lens can take `url` or `image_content` (base64). We use `url` by first uploading to
0x0.st / catbox if needed, but SerpAPI also supports direct image upload via multipart — we implement
the simpler URL approach with fallback to file upload endpoint.
"""

from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from typing import Optional

import requests

from .base import SearchResult, VisualSearchProvider

logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"


def _upload_to_0x0st(image_path: str) -> Optional[str]:
    """Upload image to https://0x0.st (free, no key, returns public URL). Returns None on failure."""
    try:
        with open(image_path, "rb") as f:
            resp = requests.post("https://0x0.st", files={"file": f}, timeout=30)
        if resp.status_code == 200 and resp.text.strip().startswith("http"):
            return resp.text.strip()
        # fallback: catbox.moe
        with open(image_path, "rb") as f:
            resp2 = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=30,
            )
        if resp2.status_code == 200 and resp2.text.strip().startswith("http"):
            return resp2.text.strip()
    except Exception as exc:  # noqa: BLE001
        logger.debug("0x0.st upload failed: %s", exc)
    return None


class SerpApiLensProvider(VisualSearchProvider):
    name = "serpapi-lens"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "SERPAPI_API_KEY not set. Get a free key at https://serpapi.com/dashboard "
                "(100 searches/month free). Set it in .env as SERPAPI_API_KEY=..."
            )

    def search(self, image_path: str, max_results: int = 10) -> list[SearchResult]:
        p = Path(image_path)
        if not p.exists():
            raise FileNotFoundError(image_path)

        # Try to get a public URL for the image (SerpAPI needs a URL)
        public_url = _upload_to_0x0st(str(p))
        if not public_url:
            # SerpAPI also supports `search?engine=google_lens&url=...` where url can be data URI?
            # Fall back to attempting without upload — will likely fail, but provide clear error
            raise RuntimeError(
                "Failed to upload image to temporary host (0x0.st / catbox.moe unavailable). "
                "Cannot perform SerpAPI Google Lens search without a public URL. Try Bing provider or retry."
            )

        params = {
            "engine": "google_lens",
            "url": public_url,
            "api_key": self.api_key,
        }
        logger.info("SerpAPI Google Lens search: %s", public_url)
        resp = requests.get(SERPAPI_ENDPOINT, params=params, timeout=45)
        if resp.status_code == 401:
            raise RuntimeError("SerpAPI authentication failed — check SERPAPI_API_KEY.")
        if resp.status_code == 429:
            raise RuntimeError("SerpAPI rate limit hit (429). Wait or upgrade plan.")
        resp.raise_for_status()
        data = resp.json()

        # SerpAPI Lens returns `visual_matches` (list)
        visual_matches = data.get("visual_matches") or data.get("image_results") or []
        if not visual_matches and "error" in data:
            raise RuntimeError(f"SerpAPI error: {data['error']}")

        results: list[SearchResult] = []
        for item in visual_matches[:max_results]:
            title = item.get("title") or item.get("source") or "Visual match"
            url = item.get("link") or item.get("source") or item.get("url") or public_url
            img = item.get("thumbnail") or item.get("image") or item.get("original") or item.get("thumbnail_url")
            thumb = item.get("thumbnail")
            source = item.get("source") or ""
            # Try to extract domain from link if source empty
            if not source and url:
                try:
                    from urllib.parse import urlparse
                    source = urlparse(url).netloc
                except Exception:
                    source = "unknown"
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    source=source,
                    image_url=img,
                    thumbnail_url=thumb,
                    metadata={"raw": item, "public_url": public_url},
                )
            )
        if not results:
            logger.warning("SerpAPI returned 0 visual_matches. Raw keys: %s", list(data.keys()))
        return results
