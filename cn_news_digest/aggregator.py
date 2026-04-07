from __future__ import annotations

from difflib import SequenceMatcher

from cn_news_digest.models import Article

SIMILARITY_THRESHOLD = 0.55


def aggregate(articles: list[Article]) -> dict[str, list[Article]]:
    """Deduplicate and group articles by source, sorted by time (newest first).

    Deduplication uses fuzzy title matching across all sources.
    """
    if not articles:
        return {}

    deduped = _deduplicate(articles)

    grouped: dict[str, list[Article]] = {}
    for article in deduped:
        grouped.setdefault(article.source, []).append(article)

    # Sort each source group by published_at descending (newest first)
    for source in grouped:
        grouped[source].sort(key=lambda a: a.published_at, reverse=True)

    return grouped


def _deduplicate(articles: list[Article]) -> list[Article]:
    """Remove articles with very similar titles, keeping the one with more metrics."""
    kept: list[Article] = []
    for article in articles:
        is_dup = False
        for i, existing in enumerate(kept):
            if _titles_similar(article.title, existing.title):
                # Keep the one with more engagement data
                if _metric_score(article) > _metric_score(existing):
                    kept[i] = article
                is_dup = True
                break
        if not is_dup:
            kept.append(article)
    return kept


def _titles_similar(a: str, b: str) -> bool:
    """Check if two titles refer to the same event."""
    return SequenceMatcher(None, a, b).ratio() > SIMILARITY_THRESHOLD


def _metric_score(article: Article) -> int:
    """Simple score based on available metrics for tie-breaking."""
    return sum(v for v in article.metrics.values() if isinstance(v, (int, float)))
