"""Integration test: verify ≥3 sources produce articles after filter + aggregate."""

import time

import pytest
import httpx
import respx
from unittest.mock import AsyncMock, patch

from cn_news_digest.cli import fetch_all
from cn_news_digest.filter import filter_articles
from cn_news_digest.aggregator import aggregate


# ---- Mock responses for each source ----

WALLSTREETCN_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>华尔街见闻</title>
  <item>
    <title>央行宣布降准0.5个百分点，释放长期资金约1万亿</title>
    <link>https://wallstreetcn.com/articles/100001</link>
    <description>中国人民银行今日宣布降准，释放长期资金</description>
    <pubDate>Mon, 07 Apr 2026 08:00:00 GMT</pubDate>
  </item>
  <item>
    <title>美联储维持利率不变，鲍威尔暗示年内降息</title>
    <link>https://wallstreetcn.com/articles/100002</link>
    <description>美联储周三宣布维持联邦基金利率不变</description>
    <pubDate>Mon, 07 Apr 2026 07:00:00 GMT</pubDate>
  </item>
</channel>
</rss>"""

SINA_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>新浪财经</title>
  <item>
    <title>A股三大指数集体收涨，半导体板块领涨</title>
    <link>https://finance.sina.com.cn/stock/001.shtml</link>
    <description>沪深两市成交额突破万亿，北向资金净买入</description>
    <pubDate>Mon, 07 Apr 2026 09:00:00 GMT</pubDate>
  </item>
  <item>
    <title>比亚迪一季度净利润同比增长45%</title>
    <link>https://finance.sina.com.cn/stock/002.shtml</link>
    <description>比亚迪发布一季度财报，净利润达120亿元</description>
    <pubDate>Mon, 07 Apr 2026 08:30:00 GMT</pubDate>
  </item>
</channel>
</rss>"""

TENCENT_API_RESPONSE = {
    "ret": 0,
    "idlist": [
        {
            "newslist": [
                {
                    "id": "header",
                    "articletype": "560",
                    "title": "热点榜",
                    "picShowType": 0,
                },
                {
                    "id": "T001",
                    "articletype": "0",
                    "title": "腾讯回购10亿港元股份，年内累计超200亿",
                    "abstract": "腾讯控股今日在公开市场回购约10亿港元股份",
                    "surl": "https://view.inews.qq.com/a/T001",
                    "time": "2026-04-07 12:00:00",
                    "readCount": 25000,
                    "commentNum": 350,
                },
                {
                    "id": "T002",
                    "articletype": "0",
                    "title": "贸易战升级：美国对华关税再加25%，出口企业承压",
                    "abstract": "中美贸易摩擦加剧，关税升级影响出口企业",
                    "surl": "https://view.inews.qq.com/a/T002",
                    "time": "2026-04-07 11:00:00",
                    "readCount": "3.5万",
                    "commentNum": 800,
                },
                {
                    "id": "T003",
                    "articletype": "0",
                    "title": "黄金价格突破2500美元，黄金ETF资金流入加速",
                    "abstract": "国际金价突破2500美元/盎司，ETF资金流入加速",
                    "surl": "https://view.inews.qq.com/a/T003",
                    "time": "2026-04-07 10:00:00",
                    "readCount": 18000,
                    "commentNum": 200,
                },
            ]
        }
    ],
}


@respx.mock
@pytest.mark.asyncio
async def test_three_sources_produce_articles():
    """End-to-end: fetch from all sources -> filter -> aggregate -> >=3 sources with data."""
    # WallStreetCN via RSSHub
    respx.get("https://rsshub.app/wallstreetcn/hot/day").mock(
        return_value=httpx.Response(200, text=WALLSTREETCN_RSS)
    )
    # Sina via RSSHub
    respx.get("https://rsshub.app/sina/finance/rollnews/2509").mock(
        return_value=httpx.Response(200, text=SINA_RSS)
    )
    # Xueqiu: RSSHub fails, Playwright not available
    respx.get("https://rsshub.app/xueqiu/hots").mock(
        return_value=httpx.Response(500)
    )
    # Tencent direct API
    respx.get("https://i.news.qq.com/gw/event/pc_hot_ranking_list").mock(
        return_value=httpx.Response(200, json=TENCENT_API_RESPONSE)
    )

    with patch("cn_news_digest.sources.xueqiu.HAS_PLAYWRIGHT", False):
        articles = await fetch_all(hours=24, top_n=15)
    assert len(articles) > 0, "Should fetch some articles"

    # Filter for investment relevance
    filtered = filter_articles(articles)
    assert len(filtered) > 0, "Some articles should pass investment filter"

    # Aggregate (dedup + group by source)
    grouped = aggregate(filtered)

    # Core assertion: at least 3 sources have articles
    sources_with_data = [s for s, arts in grouped.items() if len(arts) > 0]
    assert len(sources_with_data) >= 3, (
        f"Expected >=3 sources with data, got {len(sources_with_data)}: {sources_with_data}"
    )

    # Verify the 3 expected sources are present
    assert "wallstreetcn" in grouped, "WallStreetCN should have articles"
    assert "sina" in grouped, "Sina should have articles"
    assert "tencent" in grouped, "Tencent should have articles"


@respx.mock
@pytest.mark.asyncio
async def test_four_sources_with_xueqiu_playwright():
    """When Playwright is available, all 4 sources can produce data."""
    # WallStreetCN via RSSHub
    respx.get("https://rsshub.app/wallstreetcn/hot/day").mock(
        return_value=httpx.Response(200, text=WALLSTREETCN_RSS)
    )
    # Sina via RSSHub
    respx.get("https://rsshub.app/sina/finance/rollnews/2509").mock(
        return_value=httpx.Response(200, text=SINA_RSS)
    )
    # Xueqiu: RSSHub fails
    respx.get("https://rsshub.app/xueqiu/hots").mock(
        return_value=httpx.Response(500)
    )
    # Tencent direct API
    respx.get("https://i.news.qq.com/gw/event/pc_hot_ranking_list").mock(
        return_value=httpx.Response(200, json=TENCENT_API_RESPONSE)
    )

    # Mock Playwright to return xueqiu hot events
    mock_hot_events = [
        {
            "id": 99001,
            "tag": "#A股半导体板块大涨，北向资金净流入#",
            "content": "半导体板块集体拉升，北向资金大幅净流入",
            "status_count": 450,
        },
    ]

    mock_response = AsyncMock()
    mock_response.url = "https://xueqiu.com/hot_event/list.json?_t=123"
    mock_response.text = AsyncMock(
        return_value='{"list": ' + __import__("json").dumps(mock_hot_events) + "}"
    )

    mock_page = AsyncMock()
    response_handler = None

    def capture_on(event, handler):
        nonlocal response_handler
        if event == "response":
            response_handler = handler

    mock_page.on = capture_on

    async def fake_goto(*args, **kwargs):
        if response_handler:
            await response_handler(mock_response)

    mock_page.goto = fake_goto

    mock_ctx = AsyncMock()
    mock_ctx.new_page = AsyncMock(return_value=mock_page)
    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_ctx)
    mock_pw = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_pw_cm = AsyncMock()
    mock_pw_cm.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("cn_news_digest.sources.xueqiu.HAS_PLAYWRIGHT", True), \
         patch("cn_news_digest.sources.xueqiu.async_playwright", return_value=mock_pw_cm, create=True), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        articles = await fetch_all(hours=24, top_n=15)

    filtered = filter_articles(articles)
    grouped = aggregate(filtered)

    sources_with_data = [s for s, arts in grouped.items() if len(arts) > 0]
    assert len(sources_with_data) >= 4, (
        f"Expected 4 sources, got {len(sources_with_data)}: {sources_with_data}"
    )


@respx.mock
@pytest.mark.asyncio
async def test_graceful_degradation_all_fail():
    """When all sources fail, pipeline returns empty result without crashing."""
    respx.get("https://rsshub.app/wallstreetcn/hot/day").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://api-one-wscn.awtmt.com/apiv1/content/articles/hot").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://api-one-wscn.awtmt.com/apiv1/content/lives").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://rsshub.app/sina/finance/rollnews/2509").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://feed.mix.sina.com.cn/api/roll/get").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://rsshub.app/xueqiu/hots").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://i.news.qq.com/gw/event/pc_hot_ranking_list").mock(
        return_value=httpx.Response(500)
    )

    with patch("cn_news_digest.sources.xueqiu.HAS_PLAYWRIGHT", False):
        articles = await fetch_all(hours=24, top_n=15)
    assert articles == []
    filtered = filter_articles(articles)
    assert filtered == []
    grouped = aggregate(filtered)
    assert grouped == {}
