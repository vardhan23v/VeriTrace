"""search.provider — factory to pick the right VisualSearchProvider."""

from __future__ import annotations

import logging
import os

from .base import VisualSearchProvider
from .bing_provider import BingScrapeProvider, BingVisualSearchProvider
from .serpapi_provider import SerpApiLensProvider

logger = logging.getLogger(__name__)


def get_provider(name: str | None = None) -> VisualSearchProvider:
    """Return a VisualSearchProvider per config.

    name: "auto" | "serpapi" | "bing" | "bing_scrape" | None
    - auto: prefer serpapi if key set, else bing if key set, else bing_scrape
    """
    name = (name or os.getenv("SEARCH_PROVIDER", "auto")).strip().lower()

    if name in ("serpapi", "serpapi-lens", "google_lens"):
        return SerpApiLensProvider()

    if name in ("bing", "bing_visual"):
        return BingVisualSearchProvider()

    if name in ("bing_scrape", "scrape", "free"):
        return BingScrapeProvider()

    # auto
    serp_key = os.getenv("SERPAPI_API_KEY", "").strip()
    bing_key = os.getenv("BING_API_KEY", "").strip()

    if serp_key:
        try:
            p = SerpApiLensProvider(api_key=serp_key)
            logger.info("Using provider: serpapi-lens (key found)")
            return p
        except Exception as exc:  # noqa: BLE001
            logger.warning("SerpAPI provider init failed: %s", exc)

    if bing_key:
        try:
            p = BingVisualSearchProvider(api_key=bing_key)
            logger.info("Using provider: bing-visual (key found)")
            return p
        except Exception as exc:  # noqa: BLE001
            logger.warning("Bing Visual provider init failed: %s", exc)

    logger.info("Using provider: bing_scrape (free fallback, no key)")
    return BingScrapeProvider()
