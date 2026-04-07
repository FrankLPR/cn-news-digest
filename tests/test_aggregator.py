import pytest
from cn_news_digest.aggregator import aggregate


def test_group_by_source(sample_articles):
    grouped = aggregate(sample_articles)
    assert "wallstreetcn" in grouped
    assert "xueqiu" in grouped
    assert "sina" in grouped
    assert "tencent" in grouped


def test_dedup_similar_titles(sample_articles):
    """Articles 0 and 5 in sample_articles are about the same event (美联储)."""
    grouped = aggregate(sample_articles)
    # The duplicate should be removed — only one 美联储 article per source
    xueqiu_titles = [a.title for a in grouped["xueqiu"]]
    fed_articles = [t for t in xueqiu_titles if "美联储" in t or "鲍威尔" in t]
    # One of the two xueqiu 美联储 articles should be deduped
    assert len(fed_articles) <= 1


def test_sorted_by_published_time(sample_articles):
    grouped = aggregate(sample_articles)
    for source, articles in grouped.items():
        if len(articles) > 1:
            for i in range(len(articles) - 1):
                assert articles[i].published_at >= articles[i + 1].published_at


def test_empty_input():
    grouped = aggregate([])
    assert grouped == {}


def test_single_source():
    from datetime import datetime, timezone
    from cn_news_digest.models import Article

    articles = [
        Article(
            title="央行宣布降准0.5个百分点释放万亿资金",
            summary="Summary A",
            url="https://a.com",
            source="sina",
            published_at=datetime(2026, 4, 7, 10, 0, tzinfo=timezone.utc),
        ),
        Article(
            title="英伟达股价创历史新高市值突破三万亿美元",
            summary="Summary B",
            url="https://b.com",
            source="sina",
            published_at=datetime(2026, 4, 7, 11, 0, tzinfo=timezone.utc),
        ),
    ]
    grouped = aggregate(articles)
    assert len(grouped) == 1
    assert len(grouped["sina"]) == 2
    assert grouped["sina"][0].title == "英伟达股价创历史新高市值突破三万亿美元"  # newer first
