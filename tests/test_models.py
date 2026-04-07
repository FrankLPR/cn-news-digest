from datetime import datetime, timezone
from cn_news_digest.models import Article


def test_article_creation():
    a = Article(
        title="美联储维持利率不变",
        summary="美联储周三宣布维持联邦基金利率在5.25%-5.50%区间不变...",
        url="https://wallstreetcn.com/articles/123",
        source="wallstreetcn",
        published_at=datetime(2026, 4, 7, 10, 0, 0, tzinfo=timezone.utc),
        metrics={"views": 12000, "comments": 85},
        tags=["美联储", "利率"],
    )
    assert a.title == "美联储维持利率不变"
    assert a.source == "wallstreetcn"
    assert a.metrics["views"] == 12000


def test_article_defaults():
    a = Article(
        title="Test",
        summary="Summary",
        url="https://example.com",
        source="sina",
        published_at=datetime(2026, 4, 7, tzinfo=timezone.utc),
    )
    assert a.metrics == {}
    assert a.tags == []


def test_article_to_dict():
    a = Article(
        title="Test",
        summary="Summary",
        url="https://example.com",
        source="xueqiu",
        published_at=datetime(2026, 4, 7, 12, 0, 0, tzinfo=timezone.utc),
        metrics={"likes": 100},
        tags=["A股"],
    )
    d = a.to_dict()
    assert d["title"] == "Test"
    assert d["source"] == "xueqiu"
    assert d["published_at"] == "2026-04-07T12:00:00+00:00"
    assert d["metrics"] == {"likes": 100}
    assert d["tags"] == ["A股"]
