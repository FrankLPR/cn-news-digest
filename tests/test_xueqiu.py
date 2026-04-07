import json

import pytest
import httpx
import respx
from unittest.mock import AsyncMock, patch
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


def _make_playwright_mocks(hot_event_data=None, hot_posts_data=None):
    """Helper to build mock Playwright objects for XHR + in-page fetch tests."""
    mock_page = AsyncMock()
    response_handler = None

    def capture_on(event, handler):
        nonlocal response_handler
        if event == "response":
            response_handler = handler

    mock_page.on = capture_on
    # page.evaluate is called for _FETCH_HOTS_JS → returns hot posts list
    mock_page.evaluate = AsyncMock(return_value=hot_posts_data or [])

    # Build mock hot_event XHR response
    mock_event_response = None
    if hot_event_data is not None:
        mock_event_response = AsyncMock()
        mock_event_response.url = "https://xueqiu.com/hot_event/list.json?_t=123"
        mock_event_response.text = AsyncMock(
            return_value=json.dumps({"list": hot_event_data})
        )

    async def fake_goto(*args, **kwargs):
        if response_handler and mock_event_response:
            await response_handler(mock_event_response)

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

    return mock_pw_cm


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
async def test_fallback_to_playwright_events_only():
    """When RSSHub fails, Playwright intercepts hot events."""
    respx.get("https://rsshub.app/xueqiu/hots").mock(
        return_value=httpx.Response(500)
    )

    mock_hot_events = [
        {"id": 12345, "tag": "#算力芯片概念反弹，寒武纪大涨#",
         "content": "算力芯片板块今日集体反弹", "status_count": 320},
        {"id": 12346, "tag": "#比亚迪一季度销量突破百万#",
         "content": "比亚迪Q1累计销量突破100万辆", "status_count": 580},
    ]

    mock_pw_cm = _make_playwright_mocks(hot_event_data=mock_hot_events)

    with patch("cn_news_digest.sources.xueqiu.HAS_PLAYWRIGHT", True), \
         patch("cn_news_digest.sources.xueqiu.async_playwright", return_value=mock_pw_cm, create=True), \
         patch("asyncio.sleep", new_callable=AsyncMock):

        source = XueqiuSource()
        articles = await source.fetch(hours=24, top_n=15)

    assert len(articles) == 2
    titles = {a.title for a in articles}
    assert "算力芯片概念反弹，寒武纪大涨" in titles
    assert "比亚迪一季度销量突破百万" in titles


@respx.mock
@pytest.mark.asyncio
async def test_playwright_events_and_hot_posts():
    """Playwright fetches hot events via XHR and hot posts via in-page fetch."""
    respx.get("https://rsshub.app/xueqiu/hots").mock(
        return_value=httpx.Response(500)
    )

    mock_hot_events = [
        {"id": 12345, "tag": "#算力芯片概念反弹#",
         "content": "算力芯片板块今日集体反弹", "status_count": 320},
    ]

    mock_hot_posts = [
        {
            "id": 382817288, "user_id": 8106514687,
            "user": {"id": 8106514687, "screen_name": "川糖周掌门"},
            "title": "",
            "description": 'i茅台非标产品代售新规<a href="/S/SH600519">$贵州茅台(SH600519)$</a>值得关注',
            "text": 'i茅台非标产品代售新规<a href="/S/SH600519">$贵州茅台(SH600519)$</a>值得关注',
            "created_at": 1775531347000,
            "reply_count": 231, "retweet_count": 21, "like_count": 205, "fav_count": 56,
        },
        {
            "id": 382835878, "user_id": 4111857140,
            "user": {"id": 4111857140, "screen_name": "山行"},
            "title": "",
            "description": "屁股决定脑袋，说一点想法。能源上，中国虽然进口原油占消费原油的70%...",
            "text": "屁股决定脑袋，说一点想法。能源上...",
            "created_at": 1775520000000,
            "reply_count": 100, "like_count": 80,
        },
    ]

    mock_pw_cm = _make_playwright_mocks(
        hot_event_data=mock_hot_events, hot_posts_data=mock_hot_posts
    )

    with patch("cn_news_digest.sources.xueqiu.HAS_PLAYWRIGHT", True), \
         patch("cn_news_digest.sources.xueqiu.async_playwright", return_value=mock_pw_cm, create=True), \
         patch("asyncio.sleep", new_callable=AsyncMock):

        source = XueqiuSource()
        articles = await source.fetch(hours=24, top_n=15)

    # 1 hot event + 2 hot posts = 3 articles
    assert len(articles) == 3

    # Check hot post with stock tag
    maotai_post = [a for a in articles if "茅台" in a.title][0]
    assert maotai_post.url == "https://xueqiu.com/8106514687/382817288"
    assert "贵州茅台" in maotai_post.tags
    assert maotai_post.metrics["reply_count"] == 231
    assert maotai_post.metrics["like_count"] == 205

    # Check post without stock tags
    shanxing = [a for a in articles if "屁股决定脑袋" in a.title][0]
    assert shanxing.url == "https://xueqiu.com/4111857140/382835878"
    assert shanxing.tags == []

    # Hot event still present
    event_articles = [a for a in articles if "discussions" in a.metrics]
    assert len(event_articles) == 1


def test_parse_hot_post_stock_tags():
    """Stock tags are correctly extracted from post text."""
    item = {
        "id": 100, "user_id": 200,
        "title": "看好白酒板块",
        "text": '重点关注$贵州茅台(SH600519)$和$五粮液(SZ000858)$',
        "created_at": 1712505600000,
        "reply_count": 5, "like_count": 10,
    }
    article = XueqiuSource._parse_hot_post(item)
    assert article.tags == ["贵州茅台", "五粮液"]
    assert article.title == "看好白酒板块"
    assert article.url == "https://xueqiu.com/200/100"
    assert article.metrics["reply_count"] == 5


def test_parse_hot_post_no_title_uses_description():
    """When title is empty, falls back to description/text content."""
    item = {
        "id": 101, "user_id": 300,
        "title": "",
        "description": "这是一段很长的描述内容" * 10,
        "text": "",
        "created_at": 1712505600000,
    }
    article = XueqiuSource._parse_hot_post(item)
    assert len(article.title) == 60


def test_dedup_by_url():
    """Duplicate articles with the same URL are removed."""
    from datetime import datetime, timezone
    from cn_news_digest.models import Article

    now = datetime.now(timezone.utc)
    articles = [
        Article(title="A", summary="s1", url="https://xueqiu.com/hot_event/1",
                source="xueqiu", published_at=now, metrics={"discussions": 10}),
        Article(title="A copy", summary="s2", url="https://xueqiu.com/hot_event/1",
                source="xueqiu", published_at=now, metrics={"discussions": 20}),
        Article(title="B", summary="s3", url="https://xueqiu.com/123/456",
                source="xueqiu", published_at=now),
    ]
    result = XueqiuSource._dedup_articles(articles)
    assert len(result) == 2
    assert result[0].title == "A"


def test_dedup_fallback_no_url():
    """Articles with empty URL dedup by source+title+summary."""
    from datetime import datetime, timezone
    from cn_news_digest.models import Article

    now = datetime.now(timezone.utc)
    articles = [
        Article(title="Same", summary="Same summary", url="",
                source="xueqiu", published_at=now),
        Article(title="Same", summary="Same summary", url="",
                source="xueqiu", published_at=now),
        Article(title="Different", summary="Different summary", url="",
                source="xueqiu", published_at=now),
    ]
    result = XueqiuSource._dedup_articles(articles)
    assert len(result) == 2


@respx.mock
@pytest.mark.asyncio
async def test_hot_posts_not_squeezed_by_timeless_events():
    """When top_n is small, hot posts with real timestamps sort above
    timeless events (datetime.min)."""
    respx.get("https://rsshub.app/xueqiu/hots").mock(
        return_value=httpx.Response(500)
    )

    mock_hot_events = [
        {"id": i, "tag": f"#事件{i}#", "content": f"事件内容{i}", "status_count": 100}
        for i in range(1, 4)
    ]

    mock_hot_posts = [
        {
            "id": 900 + i, "user_id": 1000 + i,
            "title": f"热门帖子{i}", "text": f"帖子内容{i}",
            "created_at": 1712505600000 + i * 3600000,
            "reply_count": 50 + i,
        }
        for i in range(1, 4)
    ]

    mock_pw_cm = _make_playwright_mocks(
        hot_event_data=mock_hot_events, hot_posts_data=mock_hot_posts
    )

    with patch("cn_news_digest.sources.xueqiu.HAS_PLAYWRIGHT", True), \
         patch("cn_news_digest.sources.xueqiu.async_playwright", return_value=mock_pw_cm, create=True), \
         patch("asyncio.sleep", new_callable=AsyncMock):

        source = XueqiuSource()
        articles = await source.fetch(hours=9999, top_n=4)

    # 3 posts (real timestamps) sort above 3 events (datetime.min)
    post_urls = [a.url for a in articles if "/hot_event/" not in a.url]
    assert len(post_urls) == 3


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
    with patch("cn_news_digest.sources.xueqiu.HAS_PLAYWRIGHT", True), \
         patch("cn_news_digest.sources.xueqiu.async_playwright", side_effect=Exception("browser error"), create=True):
        source = XueqiuSource()
        articles = await source.fetch(hours=24, top_n=15)
    assert articles == []
