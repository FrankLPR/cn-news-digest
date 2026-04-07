from __future__ import annotations

from abc import ABC, abstractmethod

from cn_news_digest.models import Article


class BaseSource(ABC):
    """Abstract base class for all news sources."""

    name: str  # e.g., "wallstreetcn"
    display_name: str  # e.g., "华尔街见闻"

    @abstractmethod
    async def fetch(self, hours: int = 12, top_n: int = 15) -> list[Article]:
        """Fetch top articles from the past `hours` hours.

        Returns up to `top_n` articles sorted by source-native popularity.
        Returns empty list on failure (graceful degradation).
        """
        ...
