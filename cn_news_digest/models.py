from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Article:
    """A single news article from any source."""

    title: str
    summary: str
    url: str
    source: str  # "wallstreetcn" | "xueqiu" | "sina" | "tencent"
    published_at: datetime
    metrics: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat(),
            "metrics": self.metrics,
            "tags": self.tags,
        }
