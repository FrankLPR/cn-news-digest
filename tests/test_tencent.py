import pytest
import httpx
import respx
from cn_news_digest.sources.tencent import TencentFinanceSource

SAMPLE_API_RESPONSE = {
    "ret": 0,
    "idlist": [
        {
            "newslist": [
                {
                    "id": "header",
                    "articletype": "560",
                    "title": "腾讯新闻用户最关注的热点，每10分钟更新一次",
                    "picShowType": 0,
                },
                {
                    "id": "20260407A001",
                    "articletype": "0",
                    "title": "腾讯回购10亿港元股份，年内累计超200亿",
                    "abstract": "腾讯控股今日在公开市场回购约10亿港元股份...",
                    "surl": "https://view.inews.qq.com/a/20260407A001",
                    "url": "https://new.qq.com/rain/a/20260407A001",
                    "time": "2026-04-07 12:00:00",
                    "readCount": 25000,
                    "commentNum": 350,
                    "source": "腾讯财经",
                },
                {
                    "id": "20260407A002",
                    "articletype": "0",
                    "title": "苹果发布新款MacBook，搭载M4芯片",
                    "abstract": "苹果公司今日发布全新MacBook系列...",
                    "surl": "https://view.inews.qq.com/a/20260407A002",
                    "url": "https://new.qq.com/rain/a/20260407A002",
                    "time": "2026-04-07 10:00:00",
                    "readCount": "4.2万",
                    "commentNum": 500,
                    "source": "科技频道",
                },
            ]
        }
    ],
}


@respx.mock
@pytest.mark.asyncio
async def test_fetch_via_direct_api():
    respx.get("https://i.news.qq.com/gw/event/pc_hot_ranking_list").mock(
        return_value=httpx.Response(200, json=SAMPLE_API_RESPONSE)
    )
    source = TencentFinanceSource()
    articles = await source.fetch(hours=24, top_n=15)
    assert len(articles) == 2  # header placeholder skipped
    assert articles[0].source == "tencent"
    assert "腾讯" in articles[0].title


@respx.mock
@pytest.mark.asyncio
async def test_api_fail_returns_empty():
    respx.get("https://i.news.qq.com/gw/event/pc_hot_ranking_list").mock(
        return_value=httpx.Response(500)
    )
    source = TencentFinanceSource()
    articles = await source.fetch(hours=24, top_n=15)
    assert articles == []


@respx.mock
@pytest.mark.asyncio
async def test_metrics_populated():
    respx.get("https://i.news.qq.com/gw/event/pc_hot_ranking_list").mock(
        return_value=httpx.Response(200, json=SAMPLE_API_RESPONSE)
    )
    source = TencentFinanceSource()
    articles = await source.fetch(hours=24, top_n=15)
    assert articles[0].metrics.get("views") == 25000
    assert articles[0].metrics.get("comments") == 350
    # Test "4.2万" string parsing
    assert articles[1].metrics.get("views") == 42000


@respx.mock
@pytest.mark.asyncio
async def test_skips_header_placeholder():
    respx.get("https://i.news.qq.com/gw/event/pc_hot_ranking_list").mock(
        return_value=httpx.Response(200, json=SAMPLE_API_RESPONSE)
    )
    source = TencentFinanceSource()
    articles = await source.fetch(hours=24, top_n=15)
    for a in articles:
        assert "每10分钟更新" not in a.title
