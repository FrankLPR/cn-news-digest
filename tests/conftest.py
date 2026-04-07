import pytest
from datetime import datetime, timezone, timedelta
from cn_news_digest.models import Article


@pytest.fixture
def sample_articles():
    """A list of sample articles from different sources for testing."""
    now = datetime.now(timezone.utc)
    return [
        Article(
            title="美联储维持利率不变，鲍威尔暗示年内降息",
            summary="美联储周三宣布维持联邦基金利率在5.25%-5.50%区间不变，但鲍威尔在新闻发布会上暗示今年可能降息...",
            url="https://wallstreetcn.com/articles/001",
            source="wallstreetcn",
            published_at=now - timedelta(hours=2),
            metrics={"views": 50000, "comments": 320},
            tags=["美联储", "利率", "降息"],
        ),
        Article(
            title="英伟达股价创新高，市值突破3万亿美元",
            summary="英伟达周三股价大涨5%，市值首次突破3万亿美元大关，成为全球市值第二大公司...",
            url="https://xueqiu.com/statuses/002",
            source="xueqiu",
            published_at=now - timedelta(hours=3),
            metrics={"likes": 2000, "comments": 450, "reposts": 180},
            tags=["英伟达", "美股", "AI"],
        ),
        Article(
            title="A股三大指数集体收涨，半导体板块领涨",
            summary="4月7日，A股三大指数集体收涨，上证指数涨0.8%，深证成指涨1.2%，创业板指涨1.5%...",
            url="https://finance.sina.com.cn/stock/003",
            source="sina",
            published_at=now - timedelta(hours=1),
            metrics={},
            tags=["A股", "半导体"],
        ),
        Article(
            title="腾讯回购10亿港元股份，年内累计超200亿",
            summary="腾讯控股今日在公开市场回购约10亿港元股份，年内累计回购金额已超过200亿港元...",
            url="https://finance.qq.com/a/20260407/004",
            source="tencent",
            published_at=now - timedelta(hours=4),
            metrics={"views": 8000},
            tags=["腾讯", "回购", "港股"],
        ),
        Article(
            title="苹果发布新款MacBook Pro，搭载M4芯片",
            summary="苹果公司今日发布全新MacBook Pro系列，搭载最新M4芯片，性能提升40%...",
            url="https://finance.qq.com/a/20260407/005",
            source="tencent",
            published_at=now - timedelta(hours=5),
            metrics={"views": 15000},
            tags=["苹果", "科技"],
        ),
        # Duplicate of article 0 from different source (for dedup testing)
        Article(
            title="美联储按兵不动，鲍威尔释放降息信号",
            summary="北京时间周四凌晨，美联储宣布维持利率不变，主席鲍威尔在发布会上暗示年内可能降息...",
            url="https://xueqiu.com/statuses/006",
            source="xueqiu",
            published_at=now - timedelta(hours=2, minutes=30),
            metrics={"likes": 800, "comments": 120, "reposts": 50},
            tags=["美联储", "降息"],
        ),
    ]
