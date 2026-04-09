from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import httpx

from cn_news_digest.models import Article, CST
from cn_news_digest.rsshub import RSSHubClient
from cn_news_digest.sources.base import BaseSource

DIRECT_API_HOT = "https://api-one-wscn.awtmt.com/apiv1/content/articles/hot"
DIRECT_API_LIVES = "https://api-one-wscn.awtmt.com/apiv1/content/lives"
TIMEOUT = 10.0

WSCN_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Origin": "https://wallstreetcn.com",
    "Referer": "https://wallstreetcn.com/",
}


class WallStreetCNSource(BaseSource):
    name = "wallstreetcn"
    display_name = "华尔街见闻"

    def __init__(self, rsshub: RSSHubClient | None = None):
        self.rsshub = rsshub or RSSHubClient()

    async def fetch(self, hours: int = 12, top_n: int = 15) -> list[Article]:
        articles = await self._fetch_rsshub(hours, top_n)
        if not articles:
            articles = await self._fetch_direct(hours, top_n)
        return articles[:top_n]

    async def _fetch_rsshub(self, hours: int, top_n: int) -> list[Article]:
        entries = await self.rsshub.fetch_feed("/wallstreetcn/hot/day")
        if not entries:
            return []

        cutoff = datetime.now(CST) - timedelta(hours=hours)
        articles = []
        for entry in entries:
            pub_date = self._parse_rss_date(entry.get("published", ""))
            if pub_date and pub_date < cutoff:
                continue
            articles.append(
                Article(
                    title=entry.get("title", "").strip(),
                    summary=self._clean_summary(entry.get("summary", "")),
                    url=entry.get("link", ""),
                    source=self.name,
                    published_at=pub_date or datetime.now(CST),
                    metrics={},
                    tags=[],
                )
            )
        return articles

    async def _fetch_direct(self, hours: int, top_n: int) -> list[Article]:
        cutoff = datetime.now(CST) - timedelta(hours=hours)
        articles: list[Article] = []

        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            # Fetch hot articles
            articles.extend(await self._fetch_hot(client, cutoff))
            # Fetch 7x24 lives (real-time news flashes)
            articles.extend(await self._fetch_lives(client, cutoff))

        # Dedup by URL, sort newest first, take top_n
        seen_urls: set[str] = set()
        deduped: list[Article] = []
        for a in sorted(articles, key=lambda x: x.published_at, reverse=True):
            if a.url not in seen_urls:
                seen_urls.add(a.url)
                deduped.append(a)
        return deduped

    async def _fetch_hot(self, client: httpx.AsyncClient, cutoff: datetime) -> list[Article]:
        try:
            resp = await client.get(
                DIRECT_API_HOT,
                params={"period": "all"},
                headers=WSCN_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException, ValueError):
            return []

        articles = []
        for item in data.get("data", {}).get("day_items", []):
            pub_date = datetime.fromtimestamp(
                item.get("display_time", 0), tz=CST
            )
            if pub_date < cutoff:
                continue
            articles.append(
                Article(
                    title=item.get("title", "").strip(),
                    summary="",
                    url=item.get("uri", ""),
                    source=self.name,
                    published_at=pub_date,
                    metrics={
                        k: v
                        for k, v in {
                            "views": item.get("pageviews"),
                            "comments": item.get("comment_count"),
                        }.items()
                        if v
                    },
                    tags=[],
                )
            )
        return articles

    async def _fetch_lives(self, client: httpx.AsyncClient, cutoff: datetime) -> list[Article]:
        try:
            resp = await client.get(
                DIRECT_API_LIVES,
                params={"channel": "global-channel", "limit": 20},
                headers=WSCN_HEADERS,
            )
            resp.raise_for_status()
            data = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException, ValueError):
            return []

        articles = []
        for item in data.get("data", {}).get("items", []):
            pub_date = datetime.fromtimestamp(
                item.get("display_time", 0), tz=CST
            )
            if pub_date < cutoff:
                continue
            title = item.get("content_text", "").strip()
            if not title:
                continue
            # Lives are short flashes — title IS the content, truncate for display
            if len(title) > 80:
                display_title = title[:80] + "..."
            else:
                display_title = title
            articles.append(
                Article(
                    title=display_title,
                    summary=title,
                    url=item.get("uri", ""),
                    source=self.name,
                    published_at=pub_date,
                    metrics={},
                    tags=[],
                )
            )
        return articles

    @staticmethod
    def _parse_rss_date(date_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _clean_summary(text: str, max_len: int = 200) -> str:
        text = re.sub(r"<[^>]+>", "", text).strip()
        if len(text) > max_len:
            text = text[:max_len] + "..."
        return text
