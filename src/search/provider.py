"""search.provider — factory to pick the right VisualSearchProvider.

Provider order for ``auto``:
  1. serpapi  — Google Lens via SerpAPI (reverse-image, needs SERPAPI_API_KEY)
  2. bing     — Azure Bing Visual Search (reverse-image, needs BING_API_KEY)
  3. yandex   — Yandex CBIR (reverse-image, **no key**)  ← default when no keys are set

``bing_scrape`` is a text search, not reverse-image, and is never chosen automatically.
"""

from __future__ import annotations

import logging
import os

from .base import VisualSearchProvider
from .bing_provider import BingScrapeProvider, BingVisualSearchProvider
from .serpapi_provider import SerpApiLensProvider
from .yandex_provider import YandexReverseImageProvider

logger = logging.getLogger(__name__)

PROVIDER_NAMES = ("auto", "serpapi", "bing", "yandex", "bing_scrape")


def get_provider(name: str | None = None, image_url: str | None = None) -> VisualSearchProvider:
    """Return a VisualSearchProvider.

    name: "auto" | "serpapi" | "bing" | "yandex" | "bing_scrape" | None (→ $SEARCH_PROVIDER or auto)
    image_url: optional public URL of the input image (lets URL-based providers skip the upload step)
    """
    name = (name or os.getenv("SEARCH_PROVIDER", "auto")).strip().lower()

    if name in ("serpapi", "serpapi-lens", "google_lens", "lens"):
        return SerpApiLensProvider(image_url=image_url)
    if name in ("bing", "bing_visual", "bing-visual"):
        return BingVisualSearchProvider()
    if name in ("yandex", "yandex_cbir", "cbir"):
        return YandexReverseImageProvider(image_url=image_url)
    if name in ("bing_scrape", "scrape", "text"):
        return BingScrapeProvider()
    if name != "auto":
        raise ValueError(f"Unknown SEARCH_PROVIDER '{name}'. Choose one of: {', '.join(PROVIDER_NAMES)}")

    if os.getenv("SERPAPI_API_KEY", "").strip():
        logger.info("Provider: serpapi (Google Lens) — key found")
        return SerpApiLensProvider(image_url=image_url)
    if os.getenv("BING_API_KEY", "").strip():
        logger.info("Provider: bing-visual — key found")
        return BingVisualSearchProvider()
    logger.info("Provider: yandex (keyless reverse-image search)")
    return YandexReverseImageProvider(image_url=image_url)
