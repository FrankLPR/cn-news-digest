import pytest
from datetime import datetime, timezone
from cn_news_digest.models import Article
from cn_news_digest.filter import filter_articles


def _make(title: str, tags: list[str] | None = None, source: str = "sina") -> Article:
    return Article(
        title=title,
        summary="",
        url="https://example.com",
        source=source,
        published_at=datetime.now(timezone.utc),
        tags=tags or [],
    )


def test_investment_filter_keeps_stock_news():
    articles = [
        _make("A股三大指数集体收涨"),
        _make("央行宣布降准0.5个百分点"),
        _make("英伟达股价创历史新高，市值突破3万亿"),
    ]
    result = filter_articles(articles)
    assert len(result) == 3


def test_investment_filter_removes_non_investment():
    articles = [
        _make("苹果发布新款MacBook，性能大幅提升"),
        _make("今日娱乐圈八卦"),
        _make("世界杯预选赛中国队出线"),
    ]
    result = filter_articles(articles)
    assert len(result) == 0


def test_investment_filter_uses_tags():
    articles = [
        _make("某公司最新动态", tags=["A股", "半导体"]),
    ]
    result = filter_articles(articles)
    assert len(result) == 1


def test_keyword_filter():
    articles = [
        _make("英伟达Q1营收超预期"),
        _make("比亚迪销量创新高"),
        _make("央行降准释放流动性"),
    ]
    result = filter_articles(articles, keywords=["英伟达", "AI"])
    assert len(result) == 1
    assert "英伟达" in result[0].title


def test_keyword_filter_case_insensitive():
    articles = [
        _make("NVIDIA股价创新高，市值突破"),
        _make("nvidia stock美股大涨"),
    ]
    result = filter_articles(articles, keywords=["nvidia"])
    assert len(result) == 2


def test_keyword_filter_matches_summary():
    articles = [
        Article(
            title="半导体行业动态",
            summary="英伟达作为AI芯片龙头，持续受益于算力需求增长",
            url="https://example.com",
            source="sina",
            published_at=datetime.now(timezone.utc),
        ),
    ]
    result = filter_articles(articles, keywords=["英伟达"])
    assert len(result) == 1


def test_no_keywords_returns_all_investment_articles():
    articles = [
        _make("A股大涨"),
        _make("美股下跌"),
    ]
    result = filter_articles(articles, keywords=None)
    assert len(result) == 2


# --- New tests for blacklist + 2-keyword threshold ---

def test_blacklist_rejects_non_investment():
    """Articles matching NON_INVESTMENT_KEYWORDS are rejected even if they hit investment keywords."""
    articles = [
        _make("渔民捕获金枪鱼，总市值超10万", source="tencent"),
        _make("食其家创始人心梗去世，股价影响", source="tencent"),
        _make("世界杯预选赛引发股市波动", source="tencent"),
    ]
    result = filter_articles(articles)
    assert len(result) == 0


def test_tencent_requires_two_keywords():
    """Non-finance sources (tencent) need ≥2 investment keyword hits."""
    articles = [
        # Only 1 hit ("市值") — should be filtered out
        _make("某地特产总市值超百万", source="tencent"),
        # 2 hits ("回购" + "港股") — should pass
        _make("腾讯回购10亿港元股份，港股收涨", source="tencent"),
    ]
    result = filter_articles(articles)
    assert len(result) == 1
    assert "腾讯" in result[0].title


def test_finance_source_single_keyword_ok():
    """Finance sources (sina, wallstreetcn, xueqiu) only need 1 hit."""
    articles = [
        _make("央行最新政策解读", source="sina"),
        _make("央行最新政策解读", source="wallstreetcn"),
        _make("央行最新政策解读", source="xueqiu"),
    ]
    result = filter_articles(articles)
    assert len(result) == 3


def test_blacklist_overrides_investment_keywords():
    """Blacklist takes priority over investment keyword matches."""
    articles = [
        # Has "娱乐" (blacklist) + "股价" (investment) — blacklist wins
        _make("娱乐圈明星投资股价暴涨", source="sina"),
    ]
    result = filter_articles(articles)
    assert len(result) == 0
