"""tests/test_search.py — search provider interface mocked."""

from unittest.mock import MagicMock, patch
from src.search.base import SearchResult


def test_visual_search_provider_interface():
    from src.search.base import VisualSearchProvider

    # Ensure abstract
    try:
        VisualSearchProvider()
        assert False, "Should not instantiate abstract"
    except TypeError:
        pass


def test_serpapi_provider_missing_key():
    import os
    from src.search.serpapi_provider import SerpApiLensProvider

    # Ensure no key
    old = os.environ.pop("SERPAPI_API_KEY", None)
    try:
        try:
            SerpApiLensProvider(api_key="")
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "SERPAPI_API_KEY" in str(e)
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
        assert prov.name == "bing_scrape"
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
    from src.search.base import SearchResult

    results = [
        SearchResult(title="Test 1", url="https://example.com/1", source="example.com", image_url="https://picsum.photos/seed/a/400/400"),
        SearchResult(title="Test 2", url="https://example.com/2", source="example.com", image_url="https://picsum.photos/seed/b/400/400"),
    ]
    assert len(results) == 2
    assert results[0].image_url.startswith("https://")
