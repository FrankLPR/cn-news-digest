import pytest
import httpx
import respx
from unittest.mock import AsyncMock, MagicMock, patch
from cn_news_digest.sources.xueqiu import XueqiuSource

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>雪球热帖</title>
  <item>
    <title>为什么我重仓英伟达？深度解析AI算力投资逻辑</title>
    <link>https://xueqiu.com/1234567/290000001</link>
    <description>英伟达作为AI基础设施的核心供应商，其GPU产品在数据中心市场占据绝对主导地位...</description>
    <pubDate>Mon, 07 Apr 2026 09:00:00 GMT</pubDate>
    <author>投资老张</author>
  </item>
  <item>
    <title>今日A股复盘：半导体板块强势领涨</title>
    <link>https://xueqiu.com/1234567/290000002</link>
    <description>今日A股三大指数集体上涨，半导体板块涨幅居前...</description>
    <pubDate>Mon, 07 Apr 2026 07:00:00 GMT</pubDate>
    <author>股市日记</author>
  </item>
</channel>
</rss>"""


@respx.mock
@pytest.mark.asyncio
async def test_fetch_via_rsshub():
    respx.get("https://rsshub.app/xueqiu/hots").mock(
        return_value=httpx.Response(200, text=SAMPLE_RSS)
    )
    source = XueqiuSource()
    articles = await source.fetch(hours=24, top_n=15)
    assert len(articles) > 0
    assert articles[0].source == "xueqiu"
    assert "英伟达" in articles[0].title


@respx.mock
@pytest.mark.asyncio
async def test_fallback_to_playwright():
    """When RSSHub fails, falls back to Playwright XHR interception."""
    respx.get("https://rsshub.app/xueqiu/hots").mock(
        return_value=httpx.Response(500)
    )

    # Mock the playwright path
    mock_hot_events = [
        {
            "id": 12345,
            "tag": "#算力芯片概念反弹，寒武纪大涨#",
            "content": "算力芯片板块今日集体反弹，寒武纪涨超10%",
            "status_count": 320,
        },
        {
            "id": 12346,
            "tag": "#比亚迪一季度销量突破百万#",
            "content": "比亚迪Q1累计销量突破100万辆，继续领跑新能源",
            "status_count": 580,
        },
    ]

    # Create mock playwright objects
    mock_response = AsyncMock()
    mock_response.url = "https://xueqiu.com/hot_event/list.json?_t=123"
    mock_response.text = AsyncMock(
        return_value='{"list": ' + __import__("json").dumps(mock_hot_events) + "}"
    )

    mock_page = AsyncMock()
    # Capture the response handler
    response_handler = None

    def capture_on(event, handler):
        nonlocal response_handler
        if event == "response":
            response_handler = handler

    mock_page.on = capture_on
    mock_page.goto = AsyncMock()

    mock_ctx = AsyncMock()
    mock_ctx.new_page = AsyncMock(return_value=mock_page)

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_ctx)

    mock_pw = AsyncMock()
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

    # Patch async_playwright context manager
    mock_pw_cm = AsyncMock()
    mock_pw_cm.__aenter__ = AsyncMock(return_value=mock_pw)
    mock_pw_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("cn_news_digest.sources.xueqiu.HAS_PLAYWRIGHT", True), \
         patch("cn_news_digest.sources.xueqiu.async_playwright", return_value=mock_pw_cm, create=True), \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

        # Make goto trigger the response handler
        async def fake_goto(*args, **kwargs):
            if response_handler:
                await response_handler(mock_response)

        mock_page.goto = fake_goto

        source = XueqiuSource()
        articles = await source.fetch(hours=24, top_n=15)

    assert len(articles) == 2
    assert articles[0].source == "xueqiu"
    assert "算力芯片概念反弹" in articles[0].title
    assert articles[0].metrics.get("discussions") == 320
    assert articles[1].metrics.get("discussions") == 580


@respx.mock
@pytest.mark.asyncio
async def test_no_playwright_returns_empty():
    """When playwright is not installed, returns empty gracefully."""
    respx.get("https://rsshub.app/xueqiu/hots").mock(
        return_value=httpx.Response(500)
    )

    with patch("cn_news_digest.sources.xueqiu.HAS_PLAYWRIGHT", False):
        source = XueqiuSource()
        articles = await source.fetch(hours=24, top_n=15)

    assert articles == []


@respx.mock
@pytest.mark.asyncio
async def test_both_fail_returns_empty():
    respx.get("https://rsshub.app/xueqiu/hots").mock(
        return_value=httpx.Response(500)
    )
    # Playwright raises exception
    with patch("cn_news_digest.sources.xueqiu.HAS_PLAYWRIGHT", True), \
         patch("cn_news_digest.sources.xueqiu.async_playwright", side_effect=Exception("browser error"), create=True):
        source = XueqiuSource()
        articles = await source.fetch(hours=24, top_n=15)

    assert articles == []
