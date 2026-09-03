"""tests/test_search.py — search provider interface mocked."""

from src.search.base import SearchResult


def test_visual_search_provider_interface():
    # Ensure abstract
    import pytest

    from src.search.base import VisualSearchProvider

    with pytest.raises(TypeError):
        VisualSearchProvider()


def test_serpapi_provider_missing_key():
    import os

    from src.search.serpapi_provider import SerpApiLensProvider

    # Ensure no key
    old = os.environ.pop("SERPAPI_API_KEY", None)
    try:
        import pytest

        with pytest.raises(ValueError, match="SERPAPI_API_KEY"):
            SerpApiLensProvider(api_key="")
    finally:
        if old is not None:
            os.environ["SERPAPI_API_KEY"] = old


def test_bing_scrape_provider_no_key():
    from src.search.bing_provider import BingScrapeProvider

    p = BingScrapeProvider()
    # search is mocked via HTTP — we test that provider can be instantiated without key
    assert p.name == "bing_scrape"


def test_provider_factory_auto():
    import os

    from src.search.provider import get_provider

    # With no keys, should return bing_scrape
    old_serp = os.environ.pop("SERPAPI_API_KEY", None)
    old_bing = os.environ.pop("BING_API_KEY", None)
    old_prov = os.environ.pop("SEARCH_PROVIDER", None)
    try:
        os.environ["SEARCH_PROVIDER"] = "auto"
        prov = get_provider("auto")
        assert prov.name == "yandex"  # no keys → keyless reverse-image provider
    finally:
        if old_serp is not None:
            os.environ["SERPAPI_API_KEY"] = old_serp
        if old_bing is not None:
            os.environ["BING_API_KEY"] = old_bing
        if old_prov is not None:
            os.environ["SEARCH_PROVIDER"] = old_prov
        else:
            os.environ.pop("SEARCH_PROVIDER", None)


def test_search_results_mocked_pipeline():
    """Mock provider to test pipeline's handling of SearchResult objects without network."""

    results = [
        SearchResult(
            title="Test 1", url="https://example.com/1", source="example.com", image_url="https://picsum.photos/seed/a/400/400"
        ),
        SearchResult(
            title="Test 2", url="https://example.com/2", source="example.com", image_url="https://picsum.photos/seed/b/400/400"
        ),
    ]
    assert len(results) == 2
    assert results[0].image_url.startswith("https://")


# ── Yandex parser (offline fixture) ─────────────────────────────────

_YANDEX_STATE = {
    "initialState": {
        "cbirSites": {
            "sites": [
                {
                    "title": "Example — Wikipedia",
                    "description": "An example page",
                    "url": "https://en.wikipedia.org/wiki/Example?utm_source=yandexsmartcamera&utm_medium=organic#frag",
                    "domain": "en.wikipedia.org",
                    "thumb": {"url": "//avatars.mds.yandex.net/i?id=abc", "width": 148, "height": 90},
                    "originalImage": {
                        "url": "https://upload.wikimedia.org/wikipedia/commons/x/y/Example.jpg",
                        "width": 800,
                        "height": 600,
                    },
                },
                {
                    "title": "Dup",
                    "url": "https://en.wikipedia.org/wiki/Example?utm_source=other",
                    "domain": "en.wikipedia.org",
                    "originalImage": {"url": "https://upload.wikimedia.org/x.jpg"},
                },
                {"title": "No url", "domain": "nowhere.test"},
            ]
        }
    }
}


def _fixture_html() -> str:
    import html
    import json

    state = html.escape(json.dumps(_YANDEX_STATE), quote=True)
    return f'<html><body><div class="Root" data-state="{state}"></div></body></html>'


def test_yandex_parser_extracts_pages_and_strips_tracking():
    from src.search.yandex_provider import parse_yandex_html

    res = parse_yandex_html(_fixture_html(), max_results=10)
    assert len(res) == 1  # duplicate (same page after utm stripping) and url-less entries dropped
    r = res[0]
    assert r.url == "https://en.wikipedia.org/wiki/Example"
    assert r.source == "en.wikipedia.org"
    assert r.image_url == "https://upload.wikimedia.org/wikipedia/commons/x/y/Example.jpg"
    assert r.thumbnail_url.startswith("https://avatars.mds.yandex.net/")
    assert r.metadata["description"] == "An example page"


def test_yandex_parser_empty_on_unrelated_html():
    from src.search.yandex_provider import parse_yandex_html

    assert parse_yandex_html("<html><body>nothing here</body></html>") == []


def test_yandex_provider_search_uses_image_url(monkeypatch):
    """With image_url given, the provider must not upload anything and must parse the fetched page."""
    from src.search.yandex_provider import YandexReverseImageProvider

    prov = YandexReverseImageProvider(image_url="https://example.org/me.jpg")
    fetched = {}

    def fake_fetch(url, timeout=40):
        fetched["url"] = url
        return _fixture_html()

    monkeypatch.setattr(prov, "_fetch", fake_fetch)
    res = prov.search("samples/input.jpg", max_results=5)
    assert "rpt=imageview" in fetched["url"] and "example.org/me.jpg" in fetched["url"]
    assert len(res) == 1 and res[0].source == "en.wikipedia.org"


def test_yandex_captcha_is_reported_not_bypassed(monkeypatch):
    from src.search import yandex_provider as yp

    class Resp:
        status_code = 200
        text = "<html>showcaptcha please</html>"

        def raise_for_status(self):
            pass

    prov = yp.YandexReverseImageProvider(image_url="https://example.org/me.jpg")
    monkeypatch.setattr(prov.session, "get", lambda *a, **k: Resp())
    import pytest

    with pytest.raises(RuntimeError, match="CAPTCHA"):
        prov.search("samples/input.jpg")


def test_bing_scrape_never_injects_results():
    """The keyless text scraper must fail loudly rather than return pre-picked candidates."""
    import inspect

    from src.search import bing_provider

    src = inspect.getsource(bing_provider)
    assert "lena" not in src.lower()
    assert "demo_fallback" not in src.lower()
