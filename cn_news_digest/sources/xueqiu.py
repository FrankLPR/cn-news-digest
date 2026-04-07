from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import httpx

from cn_news_digest.models import Article
from cn_news_digest.rsshub import RSSHubClient
from cn_news_digest.sources.base import BaseSource

DIRECT_API_HOTS = "https://xueqiu.com/statuses/hots.json"
TIMEOUT = 10.0

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class XueqiuSource(BaseSource):
    name = "xueqiu"
    display_name = "雪球"

    def __init__(self, rsshub: RSSHubClient | None = None):
        self.rsshub = rsshub or RSSHubClient()

    async def fetch(self, hours: int = 12, top_n: int = 15) -> list[Article]:
        articles = await self._fetch_rsshub(hours, top_n)
        if not articles:
            articles = await self._fetch_playwright(hours, top_n)
        return articles[:top_n]

    async def _fetch_rsshub(self, hours: int, top_n: int) -> list[Article]:
        entries = await self.rsshub.fetch_feed("/xueqiu/hots")
        if not entries:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        articles = []
        for entry in entries:
            pub_date = self._parse_rss_date(entry.get("published", ""))
            if pub_date and pub_date < cutoff:
                continue
            articles.append(
                Article(
                    title=entry.get("title", "").strip(),
                    summary=self._clean_html(entry.get("summary", "")),
                    url=entry.get("link", ""),
                    source=self.name,
                    published_at=pub_date or datetime.now(timezone.utc),
                    metrics={},
                    tags=[],
                )
            )
        return articles

    async def _fetch_playwright(self, hours: int, top_n: int) -> list[Article]:
        """Use Playwright to intercept XHR responses from xueqiu.com."""
        if not HAS_PLAYWRIGHT:
            print("⚠ 雪球: playwright 未安装，跳过 (pip install 'cn-news-digest[browser]')", file=sys.stderr)
            return []

        hot_events: list[dict] = []

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                ctx = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/120.0.0.0 Safari/537.36"
                )
                page = await ctx.new_page()

                async def handle_response(response):
                    nonlocal hot_events
                    if "hot_event/list.json" in response.url and not hot_events:
                        try:
                            body = await response.text()
                            if body.startswith("{"):
                                data = json.loads(body)
                                hot_events = data.get("list", [])
                        except Exception:
                            pass

                page.on("response", handle_response)
                await page.goto(
                    "https://xueqiu.com",
                    wait_until="domcontentloaded",
                    timeout=20000,
                )
                await asyncio.sleep(8)
                await browser.close()
        except Exception:
            return []

        articles = []
        for item in hot_events:
            tag = item.get("tag", "")  # e.g. "#算力芯片概念反弹，寒武纪大涨#"
            content = item.get("content", "")
            title = tag.strip("#") if tag else content[:60]
            if not title:
                continue
            articles.append(
                Article(
                    title=title,
                    summary=self._clean_html(content),
                    url=f"https://xueqiu.com/hot_event/{item.get('id', '')}",
                    source=self.name,
                    published_at=datetime.now(timezone.utc),
                    metrics={"discussions": item.get("status_count", 0)},
                    tags=[],
                )
            )
        return articles[:top_n]

    @staticmethod
    def _clean_html(text: str, max_len: int = 200) -> str:
        text = re.sub(r"<[^>]+>", "", text).strip()
        if len(text) > max_len:
            text = text[:max_len] + "..."
        return text

    @staticmethod
    def _parse_rss_date(date_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            return None
