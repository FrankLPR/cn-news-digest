import pytest
import httpx
import respx
from cn_news_digest.rsshub import RSSHubClient

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>Test Feed</title>
  <item>
    <title>美联储维持利率不变</title>
    <link>https://wallstreetcn.com/articles/123</link>
    <description>美联储周三宣布维持联邦基金利率...</description>
    <pubDate>Mon, 07 Apr 2026 10:00:00 GMT</pubDate>
  </item>
  <item>
    <title>A股三大指数收涨</title>
    <link>https://wallstreetcn.com/articles/124</link>
    <description>今日A股三大指数集体收涨...</description>
    <pubDate>Mon, 07 Apr 2026 08:00:00 GMT</pubDate>
  </item>
</channel>
</rss>"""


@respx.mock
@pytest.mark.asyncio
async def test_fetch_feed_success():
    respx.get("https://rsshub.app/wallstreetcn/hot").mock(
        return_value=httpx.Response(200, text=SAMPLE_RSS)
    )
    client = RSSHubClient()
    entries = await client.fetch_feed("/wallstreetcn/hot")
    assert len(entries) == 2
    assert entries[0]["title"] == "美联储维持利率不变"
    assert "link" in entries[0]
    assert "published" in entries[0]
    assert "summary" in entries[0]


@respx.mock
@pytest.mark.asyncio
async def test_fetch_feed_custom_base_url():
    respx.get("https://my-rsshub.com/wallstreetcn/hot").mock(
        return_value=httpx.Response(200, text=SAMPLE_RSS)
    )
    client = RSSHubClient(base_url="https://my-rsshub.com")
    entries = await client.fetch_feed("/wallstreetcn/hot")
    assert len(entries) == 2


@respx.mock
@pytest.mark.asyncio
async def test_fetch_feed_failure_returns_empty():
    respx.get("https://rsshub.app/wallstreetcn/hot").mock(
        return_value=httpx.Response(500)
    )
    client = RSSHubClient()
    entries = await client.fetch_feed("/wallstreetcn/hot")
    assert entries == []


@respx.mock
@pytest.mark.asyncio
async def test_fetch_feed_timeout_returns_empty():
    respx.get("https://rsshub.app/test").mock(side_effect=httpx.TimeoutException("timeout"))
    client = RSSHubClient()
    entries = await client.fetch_feed("/test")
    assert entries == []
