from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

import httpx

from cn_news_digest.models import Article, CST
from cn_news_digest.rsshub import RSSHubClient
from cn_news_digest.sources.base import BaseSource

DIRECT_API_ROLL = "https://feed.mix.sina.com.cn/api/roll/get"
TIMEOUT = 10.0


class SinaFinanceSource(BaseSource):
    name = "sina"
    display_name = "新浪财经"

    def __init__(self, rsshub: RSSHubClient | None = None):
        self.rsshub = rsshub or RSSHubClient()

    async def fetch(self, hours: int = 12, top_n: int = 15) -> list[Article]:
        articles = await self._fetch_rsshub(hours, top_n)
        if not articles:
            articles = await self._fetch_direct(hours, top_n)
        return articles[:top_n]

    async def _fetch_rsshub(self, hours: int, top_n: int) -> list[Article]:
        entries = await self.rsshub.fetch_feed("/sina/finance/rollnews/2509")
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
                    summary=self._clean_html(entry.get("summary", "")),
                    url=entry.get("link", ""),
                    source=self.name,
                    published_at=pub_date or datetime.now(CST),
                    metrics={},
                    tags=[],
                )
            )
        return articles

    async def _fetch_direct(self, hours: int, top_n: int) -> list[Article]:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    DIRECT_API_ROLL,
                    params={
                        "pageid": 153,
                        "lid": 2509,
                        "num": top_n,
                        "page": 1,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException, ValueError):
            return []

        cutoff = datetime.now(CST) - timedelta(hours=hours)
        articles = []
        result_data = data.get("result", {}).get("data", [])
        for item in result_data:
            pub_date = self._parse_ctime(item.get("ctime", ""))
            if pub_date and pub_date < cutoff:
                continue
            articles.append(
                Article(
                    title=item.get("title", "").strip(),
                    summary=self._clean_html(
                        item.get("intro") or item.get("summary") or item.get("title", "")
                    ),
                    url=item.get("url", ""),
                    source=self.name,
                    published_at=pub_date or datetime.now(CST),
                    metrics={},
                    tags=[],
                )
            )
        return articles

    @staticmethod
    def _parse_ctime(ctime_str: str) -> datetime | None:
        """Parse Sina's ctime — Unix timestamp string (e.g. '1775552942')."""
        if not ctime_str:
            return None
        try:
            # Sina API returns Unix timestamp as string
            ts = int(ctime_str)
            return datetime.fromtimestamp(ts, tz=CST)
        except (ValueError, TypeError):
            # Fallback: try datetime format
            try:
                naive = datetime.strptime(ctime_str, "%Y-%m-%d %H:%M:%S")
                return naive.replace(tzinfo=CST)
            except ValueError:
                return None

    @staticmethod
    def _parse_rss_date(date_str: str) -> datetime | None:
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _clean_html(text: str, max_len: int = 200) -> str:
        text = re.sub(r"<[^>]+>", "", text).strip()
        if len(text) > max_len:
            text = text[:max_len] + "..."
        return text
