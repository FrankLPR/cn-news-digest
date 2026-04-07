import time

import pytest
import httpx
import respx
from cn_news_digest.sources.wallstreetcn import WallStreetCNSource

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>华尔街见闻 - 热门文章</title>
  <item>
    <title>美联储维持利率不变，鲍威尔暗示年内降息</title>
    <link>https://wallstreetcn.com/articles/123</link>
    <description>美联储周三宣布维持联邦基金利率在5.25%-5.50%区间不变，但鲍威尔在新闻发布会上暗示今年可能降息。市场反应积极，美股三大指数集体收涨。</description>
    <pubDate>Mon, 07 Apr 2026 10:00:00 GMT</pubDate>
  </item>
  <item>
    <title>原油价格大幅下跌，布伦特跌破70美元</title>
    <link>https://wallstreetcn.com/articles/124</link>
    <description>国际油价周三大幅下跌，布伦特原油期货跌破70美元/桶关口。</description>
    <pubDate>Mon, 07 Apr 2026 06:00:00 GMT</pubDate>
  </item>
</channel>
</rss>"""

SAMPLE_API_RESPONSE = {
    "code": 20000,
    "data": {
        "day_items": [
            {
                "id": 456,
                "title": "英伟达股价创历史新高",
                "uri": "https://wallstreetcn.com/articles/456",
                "display_time": int(time.time()) - 3600,
                "source_uri": "https://wallstreetcn.com/articles/456",
                "pageviews": 25000,
                "comment_count": 150,
            }
        ],
        "week_items": [],
        "offline_ids": [],
    },
}

SAMPLE_LIVES_RESPONSE = {
    "code": 20000,
    "data": {
        "items": [
            {
                "id": 789,
                "content_text": "【央行公开市场今日净投放1000亿元】中国央行今日开展2000亿元MLF操作，利率维持不变",
                "uri": "https://wallstreetcn.com/live/789",
                "display_time": int(time.time()) - 1800,
            },
            {
                "id": 790,
                "content_text": "美股期货小幅走高，纳指期货涨0.3%",
                "uri": "https://wallstreetcn.com/live/790",
                "display_time": int(time.time()) - 900,
            },
        ]
    },
}


@respx.mock
@pytest.mark.asyncio
async def test_fetch_via_rsshub():
    respx.get("https://rsshub.app/wallstreetcn/hot/day").mock(
        return_value=httpx.Response(200, text=SAMPLE_RSS)
    )
    source = WallStreetCNSource()
    articles = await source.fetch(hours=24, top_n=15)
    assert len(articles) > 0
    assert articles[0].source == "wallstreetcn"
    assert "美联储" in articles[0].title
    assert articles[0].url.startswith("https://")


@respx.mock
@pytest.mark.asyncio
async def test_fallback_to_direct_api():
    # RSSHub fails
    respx.get("https://rsshub.app/wallstreetcn/hot/day").mock(
        return_value=httpx.Response(500)
    )
    # Hot API succeeds
    respx.get("https://api-one-wscn.awtmt.com/apiv1/content/articles/hot").mock(
        return_value=httpx.Response(200, json=SAMPLE_API_RESPONSE)
    )
    # Lives API succeeds
    respx.get("https://api-one-wscn.awtmt.com/apiv1/content/lives").mock(
        return_value=httpx.Response(200, json=SAMPLE_LIVES_RESPONSE)
    )
    source = WallStreetCNSource()
    articles = await source.fetch(hours=24, top_n=15)
    # Should have 1 hot + 2 lives = 3
    assert len(articles) == 3
    assert articles[0].source == "wallstreetcn"


@respx.mock
@pytest.mark.asyncio
async def test_lives_combined_with_hot():
    """Lives and hot results are merged and deduped."""
    respx.get("https://rsshub.app/wallstreetcn/hot/day").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://api-one-wscn.awtmt.com/apiv1/content/articles/hot").mock(
        return_value=httpx.Response(200, json=SAMPLE_API_RESPONSE)
    )
    respx.get("https://api-one-wscn.awtmt.com/apiv1/content/lives").mock(
        return_value=httpx.Response(200, json=SAMPLE_LIVES_RESPONSE)
    )
    source = WallStreetCNSource()
    articles = await source.fetch(hours=24, top_n=15)
    urls = [a.url for a in articles]
    assert "https://wallstreetcn.com/articles/456" in urls
    assert "https://wallstreetcn.com/live/789" in urls
    assert "https://wallstreetcn.com/live/790" in urls
    # Sorted by time (newest first)
    for i in range(len(articles) - 1):
        assert articles[i].published_at >= articles[i + 1].published_at


@respx.mock
@pytest.mark.asyncio
async def test_lives_fail_still_returns_hot():
    """If lives API fails, hot articles still returned."""
    respx.get("https://rsshub.app/wallstreetcn/hot/day").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://api-one-wscn.awtmt.com/apiv1/content/articles/hot").mock(
        return_value=httpx.Response(200, json=SAMPLE_API_RESPONSE)
    )
    respx.get("https://api-one-wscn.awtmt.com/apiv1/content/lives").mock(
        return_value=httpx.Response(500)
    )
    source = WallStreetCNSource()
    articles = await source.fetch(hours=24, top_n=15)
    assert len(articles) == 1
    assert "英伟达" in articles[0].title


@respx.mock
@pytest.mark.asyncio
async def test_both_fail_returns_empty():
    respx.get("https://rsshub.app/wallstreetcn/hot/day").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://api-one-wscn.awtmt.com/apiv1/content/articles/hot").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://api-one-wscn.awtmt.com/apiv1/content/lives").mock(
        return_value=httpx.Response(500)
    )
    source = WallStreetCNSource()
    articles = await source.fetch(hours=24, top_n=15)
    assert articles == []
