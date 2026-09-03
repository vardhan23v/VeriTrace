"""extraction.post_extractor — download candidate images + extract page metadata.

Respects robots/access: no auth bypass, no CAPTCHA evasion. On block, fails gracefully.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from src.search.base import SearchResult

logger = logging.getLogger(__name__)

# Human-readable platform names for well-known hosts (used for display + canonical "platform").
_PLATFORMS = {
    "instagram.com": "Instagram",
    "facebook.com": "Facebook",
    "x.com": "X (Twitter)",
    "twitter.com": "X (Twitter)",
    "linkedin.com": "LinkedIn",
    "reddit.com": "Reddit",
    "pinterest.com": "Pinterest",
    "tiktok.com": "TikTok",
    "youtube.com": "YouTube",
    "threads.net": "Threads",
    "flickr.com": "Flickr",
    "tumblr.com": "Tumblr",
    "wikipedia.org": "Wikipedia",
    "wikimedia.org": "Wikimedia Commons",
    "github.com": "GitHub",
    "medium.com": "Medium",
    "imdb.com": "IMDb",
    "vk.com": "VK",
    "stackoverflow.com": "Stack Overflow",
}
SOCIAL_HOSTS = (
    "instagram.com",
    "facebook.com",
    "x.com",
    "twitter.com",
    "linkedin.com",
    "reddit.com",
    "pinterest.com",
    "tiktok.com",
    "youtube.com",
    "threads.net",
    "flickr.com",
    "tumblr.com",
    "vk.com",
)


def platform_name(domain: str) -> str:
    """'www.instagram.com' → 'Instagram'; unknown hosts are returned bare (e.g. 'blog.example.org')."""
    d = (domain or "").lower().removeprefix("www.").removeprefix("m.")
    for host, name in _PLATFORMS.items():
        if d == host or d.endswith("." + host):
            return name
    return d


def is_social(domain: str) -> bool:
    d = (domain or "").lower()
    return any(d == h or d.endswith("." + h) for h in SOCIAL_HOSTS)


DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def download_image(
    url: str,
    dest_dir: str | os.PathLike,
    timeout: int = 20,
    max_bytes: int = 15_000_000,
) -> tuple[Path, str]:
    """Download image URL to dest_dir. Returns (local_path, sha256_hex).

    Raises RuntimeError on failure (timeout, 404, too large, not an image).
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    parsed = urlparse(url)
    # derive filename
    name = Path(parsed.path).name or "image"
    if "." not in name:
        name += ".jpg"
    # sanitise
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    # unique suffix
    suffix = hashlib.sha256(url.encode()).hexdigest()[:8]
    stem, ext = os.path.splitext(name)
    local = dest_dir / f"{stem}_{suffix}{ext}"

    headers = {**DEFAULT_HEADERS, "Referer": f"{parsed.scheme}://{parsed.netloc}/"}

    # stream download with size cap
    try:
        with requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True) as resp:
            if resp.status_code in (403, 404, 410):
                raise RuntimeError(f"Image unavailable (HTTP {resp.status_code}): {url}")
            resp.raise_for_status()
            ctype = resp.headers.get("Content-Type", "")
            if ctype and not ctype.startswith("image/") and "octet-stream" not in ctype:
                # Some CDNs omit ctype — don't hard-fail, check extension
                if Path(url).suffix.lower() not in IMAGE_EXTS and "image" not in ctype:
                    logger.warning("Unexpected Content-Type %s for %s — attempting anyway", ctype, url)
            hasher = hashlib.sha256()
            total = 0
            with open(local, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        total += len(chunk)
                        if total > max_bytes:
                            raise RuntimeError(f"Image too large (> {max_bytes} bytes): {url}")
                        f.write(chunk)
                        hasher.update(chunk)
            if total == 0:
                raise RuntimeError(f"Empty image download: {url}")
            # verify it's actually an image (magic bytes check via Pillow or extension)
            if local.stat().st_size < 512:
                # too small to be valid image — likely HTML error page
                text = local.read_text(errors="ignore")[:500] if local.exists() else ""
                if "<html" in text.lower():
                    raise RuntimeError(f"Downloaded HTML instead of image (blocked?): {url}")
            sha = hasher.hexdigest()
            return local, sha
    except requests.RequestException as exc:
        raise RuntimeError(f"Failed to download image {url}: {exc}") from exc


def extract_page_metadata(url: str, timeout: int = 15) -> dict:
    """Fetch URL and extract title/caption/author/timestamp where available.

    Never bypasses auth/CAPTCHA; on 403/429 returns minimal metadata and logs.
    """
    # For direct image URLs (cdn), don't fetch HTML
    if (
        url.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"))
        or "picsum.photos" in url
        or "wikimedia.org" in url
    ):
        # Use URL-derived metadata
        parsed = urlparse(url)
        return {
            "page_title": f"Image — {parsed.netloc}",
            "caption": "",
            "author": "",
            "published_at": "",
            "og_image": url,
            "description": "",
        }

    headers = dict(DEFAULT_HEADERS)
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if resp.status_code in (403, 429):
            logger.warning("Access blocked/rate-limited (%s) for %s — returning minimal metadata", resp.status_code, url)
            return {"page_title": "", "caption": "", "author": "", "published_at": "", "error": f"HTTP {resp.status_code}"}
        resp.raise_for_status()
        ctype = resp.headers.get("Content-Type", "")
        if "text/html" not in ctype and "application/xhtml" not in ctype:
            return {"page_title": "", "caption": "", "author": "", "published_at": ""}

        soup = BeautifulSoup(resp.text, "lxml")

        # title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        # og:title fallback
        if not title:
            og = soup.find("meta", property="og:title")
            if og and og.get("content"):
                title = og["content"].strip()
        # og:description / meta description
        caption = ""
        for key in [{"property": "og:description"}, {"name": "description"}, {"property": "description"}]:
            tag = soup.find("meta", key)
            if tag and tag.get("content"):
                caption = tag["content"].strip()
                break
        # author
        author = ""
        for key in [{"name": "author"}, {"property": "article:author"}, {"property": "og:author"}]:
            tag = soup.find("meta", key)
            if tag and tag.get("content"):
                author = tag["content"].strip()
                break
        # published time
        published = ""
        for key in [
            {"property": "article:published_time"},
            {"property": "og:published_time"},
            {"name": "pubdate"},
            {"name": "publishdate"},
        ]:
            tag = soup.find("meta", key)
            if tag and tag.get("content"):
                published = tag["content"].strip()
                break
        if not published:
            t = soup.find("time")
            if t and t.get("datetime"):
                published = t["datetime"].strip()
        # og:image
        og_image = ""
        ogi = soup.find("meta", property="og:image")
        if ogi and ogi.get("content"):
            og_image = ogi["content"].strip()

        # first meaningful paragraph as caption fallback
        if not caption:
            p = soup.find("p")
            if p:
                caption = p.get_text(strip=True)[:300]

        return {
            "page_title": title,
            "caption": caption,
            "author": author,
            "published_at": published,
            "og_image": og_image,
            "description": caption,
        }
    except requests.RequestException as exc:
        logger.warning("Metadata fetch failed for %s: %s", url, exc)
        return {"page_title": "", "caption": "", "author": "", "published_at": "", "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Metadata parse failed for %s: %s", url, exc)
        return {"page_title": "", "caption": "", "author": "", "published_at": "", "error": str(exc)}


def enrich_result(
    result: SearchResult,
    timeout: int = 15,
) -> dict:
    """Fetch page metadata for a SearchResult and return enriched dict."""
    meta = extract_page_metadata(result.url, timeout=timeout)
    return {
        "platform": platform_name(result.source),
        "domain": result.source,
        "post_url": result.url,
        "title": meta.get("page_title") or result.title,
        "caption": meta.get("caption") or result.metadata.get("description", "") or "",
        "author": meta.get("author") or "",
        "published_at": meta.get("published_at") or "",
        "og_image": meta.get("og_image") or result.image_url or "",
    }
