"""search.yandex_provider — genuine reverse-image search via Yandex Images (no API key).

Yandex "search by image" (CBIR) returns the *pages that contain the query image*
("sites" block) plus visually similar images. The HTML embeds a JSON blob in a
``data-state`` attribute which we parse — no JS execution, no key.

Two ways to submit the query image:

1. ``image_url`` — if the caller already has a public URL for the input image
   (``--image-url`` / ``INPUT_IMAGE_URL``), we search by URL directly.
2. Upload — we POST the local file to Yandex's upload endpoint, which answers
   with a ``cbir_id``; we then fetch the results page for that id.
   If the upload endpoint is unavailable we fall back to a temporary public
   host (0x0.st / catbox.moe) and search by that URL.

This is a real external search step: results are whatever Yandex returns for
*this* image. Nothing is pre-picked.
"""

from __future__ import annotations

import html as html_lib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

from .base import SearchResult, VisualSearchProvider

logger = logging.getLogger(__name__)

YANDEX_SEARCH = "https://yandex.com/images/search"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
_HEADERS = {
    "User-Agent": _UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Tracking params Yandex appends to outbound links — stripped so the canonical
# post_url is stable across runs.
_TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "yclid"}


def strip_tracking(url: str) -> str:
    """Remove utm_* / click-id params so the same page always yields the same URL."""
    try:
        parts = urlparse(url)
        q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in _TRACKING_PARAMS]
        return urlunparse(parts._replace(query=urlencode(q), fragment=""))
    except Exception:  # noqa: BLE001
        return url


def _abs(url: str) -> str:
    if url.startswith("//"):
        return "https:" + url
    return url


# ── HTML parsing (pure, unit-testable) ───────────────────────────────


def parse_yandex_html(html: str, max_results: int = 10) -> list[SearchResult]:
    """Extract page-level matches from a Yandex Images CBIR results page.

    Looks for the ``initialState.cbirSites.sites`` list inside any
    ``data-state`` JSON attribute. Returns [] when nothing is found.
    """
    results: list[SearchResult] = []
    seen: set[str] = set()

    for m in re.finditer(r'data-state="([^"]+)"', html):
        raw = html_lib.unescape(m.group(1))
        if "cbirSites" not in raw and '"sites"' not in raw:
            continue
        try:
            state = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for sites in _iter_site_lists(state):
            for site in sites:
                page_url = strip_tracking(str(site.get("url") or ""))
                if not page_url.startswith("http") or page_url in seen:
                    continue
                orig = site.get("originalImage") or {}
                thumb = site.get("thumb") or {}
                image_url = _abs(str(orig.get("url") or "")) or _abs(str(thumb.get("url") or ""))
                domain = site.get("domain") or urlparse(page_url).netloc
                seen.add(page_url)
                results.append(
                    SearchResult(
                        title=(site.get("title") or f"Page on {domain}").strip(),
                        url=page_url,
                        source=domain,
                        image_url=image_url or None,
                        thumbnail_url=_abs(str(thumb.get("url") or "")) or None,
                        metadata={
                            "provider": "yandex",
                            "description": (site.get("description") or "").strip(),
                            "image_width": orig.get("width"),
                            "image_height": orig.get("height"),
                        },
                    )
                )
                if len(results) >= max_results:
                    return results
        if results:
            break
    return results


def _iter_site_lists(state: Any):
    """Yield every list found under a key named 'sites' (depth-first)."""
    stack = [state]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "sites" and isinstance(v, list):
                    yield v
                elif isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(node, list):
            stack.extend(x for x in node if isinstance(x, (dict, list)))


def _is_captcha(html: str) -> bool:
    low = html.lower()
    return "showcaptcha" in low or "smartcaptcha" in low or "are you not a robot" in low


# ── Upload helpers ───────────────────────────────────────────────────


def upload_to_yandex(image_path: str, session: requests.Session, timeout: int = 45) -> str | None:
    """Upload the image to Yandex; return the results-page URL (contains cbir_id) or None."""
    params = {
        "rpt": "imageview",
        "format": "json",
        "request": json.dumps({"blocks": [{"block": "b-page_type_search-by-image__link"}]}),
    }
    try:
        with open(image_path, "rb") as f:
            resp = session.post(
                YANDEX_SEARCH,
                params=params,
                files={"upfile": (Path(image_path).name, f, "image/jpeg")},
                headers=_HEADERS,
                timeout=timeout,
            )
        if resp.status_code != 200:
            logger.debug("Yandex upload HTTP %s", resp.status_code)
            return None
        data = resp.json()
        blocks = data.get("blocks") or []
        query = ""
        for b in blocks:
            query = (b.get("params") or {}).get("url") or query
        if not query:
            return None
        if query.startswith("http"):
            return query
        return f"{YANDEX_SEARCH}?{query.lstrip('?')}"
    except Exception as exc:  # noqa: BLE001
        logger.debug("Yandex upload failed: %s", exc)
        return None


def upload_to_temp_host(image_path: str, timeout: int = 30) -> str | None:
    """Host the image on a free temporary file host and return its public URL."""
    name = Path(image_path).name
    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                "https://0x0.st", files={"file": (name, f)}, headers={"User-Agent": "veritrace/1.0"}, timeout=timeout
            )
        if r.status_code == 200 and r.text.strip().startswith("http"):
            return r.text.strip()
    except Exception as exc:  # noqa: BLE001
        logger.debug("0x0.st upload failed: %s", exc)
    try:
        with open(image_path, "rb") as f:
            r = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (name, f)},
                timeout=timeout,
            )
        if r.status_code == 200 and r.text.strip().startswith("http"):
            return r.text.strip()
    except Exception as exc:  # noqa: BLE001
        logger.debug("catbox upload failed: %s", exc)
    return None


# ── Provider ─────────────────────────────────────────────────────────


class YandexReverseImageProvider(VisualSearchProvider):
    """Keyless reverse-image search (Yandex CBIR). See module docstring."""

    name = "yandex"

    def __init__(self, image_url: str | None = None, session: requests.Session | None = None):
        self.image_url = (image_url or os.getenv("INPUT_IMAGE_URL", "")).strip() or None
        self.session = session or requests.Session()
        self.last_query_url: str | None = None

    def _fetch(self, url: str, timeout: int = 40) -> str:
        resp = self.session.get(url, headers=_HEADERS, timeout=timeout, allow_redirects=True)
        if resp.status_code == 429:
            raise RuntimeError("Yandex rate-limited the request (429). Wait a minute and retry.")
        resp.raise_for_status()
        if _is_captcha(resp.text):
            raise RuntimeError(
                "Yandex answered with a CAPTCHA page (bot protection). VeriTrace will not bypass it — "
                "retry later, pass --image-url with a public URL, or use --provider serpapi."
            )
        return resp.text

    def search(self, image_path: str, max_results: int = 10) -> list[SearchResult]:
        p = Path(image_path)
        if not p.exists():
            raise FileNotFoundError(str(p))

        results_url: str | None = None
        how = ""

        if self.image_url:
            results_url = f"{YANDEX_SEARCH}?rpt=imageview&url={self.image_url}"
            how = "by public URL"
        else:
            results_url = upload_to_yandex(str(p), self.session)
            how = "by direct upload"
            if not results_url:
                public = upload_to_temp_host(str(p))
                if public:
                    results_url = f"{YANDEX_SEARCH}?rpt=imageview&url={public}"
                    how = f"via temp host {urlparse(public).netloc}"
        if not results_url:
            raise RuntimeError(
                "Could not submit the image to Yandex (upload endpoint and temp hosts all failed). "
                "Pass --image-url <public-url-of-this-image> or use --provider serpapi."
            )

        self.last_query_url = results_url
        logger.info("Yandex reverse-image search %s: %s", how, results_url)
        html = self._fetch(results_url)
        results = parse_yandex_html(html, max_results=max_results)
        if not results:
            logger.warning("Yandex returned no page matches for this image")
        return results
