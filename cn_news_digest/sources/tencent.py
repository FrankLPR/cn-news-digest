from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta

import httpx

from cn_news_digest.models import Article
from cn_news_digest.sources.base import BaseSource

# Tencent News hot ranking API (general hot list, investment filter applied later)
DIRECT_API_LIST = "https://i.news.qq.com/gw/event/pc_hot_ranking_list"
TIMEOUT = 10.0


class TencentFinanceSource(BaseSource):
    name = "tencent"
    display_name = "腾讯财经"

    async def fetch(self, hours: int = 12, top_n: int = 15) -> list[Article]:
        """Tencent has poor RSSHub coverage, so we go direct API only."""
        return await self._fetch_direct(hours, top_n)

    async def _fetch_direct(self, hours: int, top_n: int) -> list[Article]:
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    DIRECT_API_LIST,
                    params={
                        "ids_hash": "",
                        "offset": 0,
                        "page_size": 50,
                        "appver": "15.5_qqnews_7.1.60",
                        "rank_id": "hot",
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                        "Referer": "https://news.qq.com/",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, httpx.TimeoutException, ValueError):
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        articles = []

        # Response: {"ret": 0, "idlist": [{"newslist": [...]}]}
        idlist = data.get("idlist", [])
        if not idlist:
            return []

        newslist = idlist[0].get("newslist", [])
        for item in newslist:
            # Skip header placeholders (articletype "560")
            if item.get("articletype") == "560":
                continue

            pub_date = self._parse_publish_time(item.get("time", ""))
            if pub_date and pub_date < cutoff:
                continue

            read_count = item.get("readCount")
            comment_num = item.get("commentNum")
            metrics = {}
            if read_count:
                metrics["views"] = self._parse_count(read_count)
            if comment_num:
                metrics["comments"] = self._parse_count(comment_num)

            articles.append(
                Article(
                    title=item.get("title", "").strip(),
                    summary=self._clean_html(item.get("abstract", "")),
                    url=item.get("surl") or item.get("url", ""),
                    source=self.name,
                    published_at=pub_date or datetime.now(timezone.utc),
                    metrics=metrics,
                    tags=[],
                )
            )
        # Return all articles — this is a general hot list, not finance-specific.
        # The downstream investment filter will select relevant ones.
        return articles

    @staticmethod
    def _parse_publish_time(time_str: str) -> datetime | None:
        if not time_str:
            return None
        try:
            naive = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
            return naive.replace(tzinfo=timezone(timedelta(hours=8)))
        except ValueError:
            return None

    @staticmethod
    def _parse_count(value) -> int | None:
        """Parse count values that may be strings like '1.2万' or ints."""
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            value = value.strip()
            if value.endswith("万"):
                try:
                    return int(float(value[:-1]) * 10000)
                except ValueError:
                    return None
            try:
                return int(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _clean_html(text: str, max_len: int = 200) -> str:
        text = re.sub(r"<[^>]+>", "", text).strip()
        if len(text) > max_len:
            text = text[:max_len] + "..."
        return text
