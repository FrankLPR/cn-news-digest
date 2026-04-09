import time

import pytest
import httpx
import respx
from cn_news_digest.sources.sina import SinaFinanceSource
from tests.conftest import rss_date


def _make_sample_rss():
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>新浪财经</title>
  <item>
    <title>央行宣布降准0.5个百分点，释放长期资金约1万亿</title>
    <link>https://finance.sina.com.cn/china/2026-04-07/001.shtml</link>
    <description>中国人民银行今日宣布，决定于4月15日下调金融机构存款准备金率0.5个百分点...</description>
    <pubDate>{rss_date(2)}</pubDate>
  </item>
  <item>
    <title>两市成交额突破1.5万亿，北向资金净买入超百亿</title>
    <link>https://finance.sina.com.cn/stock/2026-04-07/002.shtml</link>
    <description>今日沪深两市成交额达1.52万亿元，北向资金全天净买入102亿元...</description>
    <pubDate>{rss_date(3)}</pubDate>
  </item>
</channel>
</rss>"""


SAMPLE_API_RESPONSE = {
    "result": {
        "status": {"code": 0},
        "data": [
            {
                "title": "中芯国际Q1营收创历史新高",
                "url": "https://finance.sina.com.cn/stock/2026-04-07/003.shtml",
                "intro": "中芯国际发布2026年第一季度财报，营收达150亿元人民币，同比增长28%...",
                "ctime": str(int(time.time()) - 3600),  # Unix timestamp string, 1 hour ago
            }
        ],
    }
}


@respx.mock
@pytest.mark.asyncio
async def test_fetch_via_rsshub():
    respx.get("https://rsshub.app/sina/finance/rollnews/2509").mock(
        return_value=httpx.Response(200, text=_make_sample_rss())
    )
    source = SinaFinanceSource()
    articles = await source.fetch(hours=24, top_n=15)
    assert len(articles) > 0
    assert articles[0].source == "sina"
    assert "央行" in articles[0].title


@respx.mock
@pytest.mark.asyncio
async def test_fallback_to_direct_api():
    respx.get("https://rsshub.app/sina/finance/rollnews/2509").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://feed.mix.sina.com.cn/api/roll/get").mock(
        return_value=httpx.Response(200, json=SAMPLE_API_RESPONSE)
    )
    source = SinaFinanceSource()
    articles = await source.fetch(hours=24, top_n=15)
    assert len(articles) > 0
    assert articles[0].source == "sina"
    assert "中芯国际" in articles[0].title


@respx.mock
@pytest.mark.asyncio
async def test_both_fail_returns_empty():
    respx.get("https://rsshub.app/sina/finance/rollnews/2509").mock(
        return_value=httpx.Response(500)
    )
    respx.get("https://feed.mix.sina.com.cn/api/roll/get").mock(
        return_value=httpx.Response(500)
    )
    source = SinaFinanceSource()
    articles = await source.fetch(hours=24, top_n=15)
    assert articles == []
