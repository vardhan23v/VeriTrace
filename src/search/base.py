"""search.base — VisualSearchProvider interface and SearchResult model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SearchResult:
    """One candidate discovered via visual/web search."""

    title: str
    url: str  # page URL (canonical)
    source: str  # platform / domain, e.g. "instagram.com"
    image_url: str | None = None  # direct image CDN URL
    thumbnail_url: str | None = None
    page_url: str | None = None  # alias for url
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.page_url is None:
            self.page_url = self.url
        # normalise source
        if self.source:
            self.source = self.source.strip().lower()


class VisualSearchProvider(ABC):
    """Abstract visual-search provider.

    Implementations must perform a *genuine* external search — no hard-coded
    URL lists, no local-DB pretending to be web search.
    """

    name: str = "base"

    @abstractmethod
    def search(self, image_path: str, max_results: int = 10) -> list[SearchResult]:
        """Search using image_path and return up to max_results candidates.

        Should raise a clear exception on auth/network failure so the pipeline
        can surface an actionable message (not a raw traceback).
        """
        ...
