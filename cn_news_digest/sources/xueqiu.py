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

# Regex to extract stock tags like "$贵州茅台(SH600519)$"
_STOCK_TAG_RE = re.compile(r"\$([^$()]+)\([A-Z]{2}\d+\)\$")

try:
    from playwright.async_api import async_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

_FETCH_HOTS_JS = """
async () => {
    try {
        const r = await fetch("https://xueqiu.com/statuses/hots.json?page=1&count=20");
        if (!r.ok) return [];
        const data = await r.json();
        return Array.isArray(data) ? data : [];
    } catch (e) {
        return [];
    }
}
"""


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
        """Use Playwright to intercept hot_event XHR and fetch hot posts via API."""
        if not HAS_PLAYWRIGHT:
            print("⚠ 雪球: playwright 未安装，跳过 (pip install 'cn-news-digest[browser]')", file=sys.stderr)
            return []

        hot_events: list[dict] = []
        hot_posts: list[dict] = []

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
                    url = response.url
                    try:
                        if "hot_event/list.json" in url and not hot_events:
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

                # Fetch hot posts via in-page fetch (uses session cookies)
                hot_posts = await page.evaluate(_FETCH_HOTS_JS)

                await browser.close()
        except Exception:
            return []

        articles: list[Article] = []

        # Parse hot events from XHR
        for item in hot_events:
            tag = item.get("tag", "")  # e.g. "#算力芯片概念反弹，寒武纪大涨#"
            content = item.get("content", "")
            title = tag.strip("#") if tag else content[:60]
            if not title:
                continue
            # Use real timestamp if available (milliseconds epoch)
            created_at_ms = item.get("created_at", 0)
            if created_at_ms:
                published_at = datetime.fromtimestamp(created_at_ms / 1000, tz=timezone.utc)
            else:
                published_at = datetime.min.replace(tzinfo=timezone.utc)
            articles.append(
                Article(
                    title=title,
                    summary=self._clean_html(content),
                    url=f"https://xueqiu.com/hot_event/{item.get('id', '')}",
                    source=self.name,
                    published_at=published_at,
                    metrics={"discussions": item.get("status_count", 0)},
                    tags=[],
                )
            )

        # Parse hot posts from statuses/hots.json API
        for item in hot_posts:
            articles.append(self._parse_hot_post(item))

        # Deduplicate by URL; for empty URLs fall back to source+title+summary
        articles = self._dedup_articles(articles)

        # Sort by published_at descending, then trim
        articles.sort(key=lambda a: a.published_at, reverse=True)
        return articles[:top_n]

    @classmethod
    def _parse_hot_post(cls, item: dict) -> Article:
        """Convert a hot post dict from statuses/hots.json into an Article."""
        text = item.get("text", "") or item.get("description", "") or ""
        title_raw = item.get("title", "") or ""
        # Clean HTML from text for summary
        clean_text = cls._clean_html(text, max_len=300)

        # Title: use explicit title if present, else first 60 chars of clean text
        title = title_raw.strip() if title_raw.strip() else clean_text[:60]

        # Extract stock tags like "$贵州茅台(SH600519)$"
        tags = _STOCK_TAG_RE.findall(text)

        # Build URL from user_id and post id
        user_id = item.get("user_id") or (item.get("user") or {}).get("id", "")
        post_id = item.get("id", "")
        url = f"https://xueqiu.com/{user_id}/{post_id}" if user_id and post_id else ""

        # Parse timestamp (milliseconds since epoch)
        created_at_ms = item.get("created_at", 0)
        if created_at_ms:
            published_at = datetime.fromtimestamp(created_at_ms / 1000, tz=timezone.utc)
        else:
            published_at = datetime.now(timezone.utc)

        metrics = {}
        for key in ("reply_count", "retweet_count", "like_count", "fav_count"):
            val = item.get(key)
            if val is not None:
                metrics[key] = val

        return Article(
            title=title,
            summary=clean_text[:200] + ("..." if len(clean_text) > 200 else ""),
            url=url,
            source="xueqiu",
            published_at=published_at,
            metrics=metrics,
            tags=tags,
        )

    @staticmethod
    def _dedup_articles(articles: list[Article]) -> list[Article]:
        """Deduplicate articles by URL; fall back to source+title+summary for empty URLs."""
        seen: set[str] = set()
        result: list[Article] = []
        for a in articles:
            key = a.url if a.url else f"{a.source}|{a.title}|{a.summary}"
            if key not in seen:
                seen.add(key)
                result.append(a)
        return result

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
