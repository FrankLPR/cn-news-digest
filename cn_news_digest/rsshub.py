from __future__ import annotations

import os

import feedparser
import httpx

DEFAULT_RSSHUB_URL = "https://rsshub.app"
TIMEOUT = 10.0


class RSSHubClient:
    """Fetches and parses RSS feeds from an RSSHub instance."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (
            base_url or os.environ.get("RSSHUB_URL") or DEFAULT_RSSHUB_URL
        ).rstrip("/")

    async def fetch_feed(self, route: str) -> list[dict]:
        """Fetch an RSS feed and return parsed entries.

        Returns a list of dicts with keys: title, link, summary, published.
        Returns empty list on any error.
        """
        url = f"{self.base_url}{route}"
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(url)
                resp.raise_for_status()
        except (httpx.HTTPError, httpx.TimeoutException):
            return []

        feed = feedparser.parse(resp.text)
        entries = []
        for entry in feed.entries:
            entries.append(
                {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "summary": entry.get("description", entry.get("summary", "")),
                    "published": entry.get("published", ""),
                }
            )
        return entries
