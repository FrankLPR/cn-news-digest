"""cn-news-digest: Fetch hot investment news from Chinese financial sources."""

__version__ = "0.1.0"

from cn_news_digest.models import Article
from cn_news_digest.sources import ALL_SOURCES
from cn_news_digest.filter import filter_articles
from cn_news_digest.aggregator import aggregate
from cn_news_digest.formatter import format_markdown, format_json
from cn_news_digest.cli import fetch_all

__all__ = [
    "Article",
    "ALL_SOURCES",
    "fetch_all",
    "filter_articles",
    "aggregate",
    "format_markdown",
    "format_json",
]
