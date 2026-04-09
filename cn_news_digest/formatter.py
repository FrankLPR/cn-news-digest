from __future__ import annotations

import json
from datetime import datetime, timezone

from cn_news_digest.models import Article, CST

SOURCE_DISPLAY_NAMES = {
    "wallstreetcn": "华尔街见闻",
    "xueqiu": "雪球",
    "sina": "新浪财经",
    "tencent": "腾讯财经",
}

# Display order
SOURCE_ORDER = ["wallstreetcn", "sina", "xueqiu", "tencent"]


def format_markdown(grouped: dict[str, list[Article]]) -> str:
    """Format grouped articles as human-readable Markdown."""
    now = datetime.now(CST).strftime("%Y-%m-%d %H:%M CST")
    total = sum(len(articles) for articles in grouped.values())

    if total == 0:
        return f"# 投资要闻\n\n> {now} 抓取，没有找到相关新闻\n"

    lines = [
        f"# 投资要闻",
        f"> {now} 抓取，共 {total} 条",
        "",
    ]

    for source_key in SOURCE_ORDER:
        if source_key not in grouped:
            continue
        articles = grouped[source_key]
        display_name = SOURCE_DISPLAY_NAMES.get(source_key, source_key)
        lines.append(f"## {display_name} ({len(articles)}条)")
        lines.append("")

        for i, article in enumerate(articles, 1):
            metrics_str = _format_metrics(article.metrics)
            time_str = article.published_at.astimezone(CST).strftime("%H:%M")
            lines.append(
                f"{i}. **{article.title}** — {article.summary}"
            )
            lines.append(f"   [{time_str}]({article.url}){metrics_str}")
            lines.append("")

    return "\n".join(lines)


def format_json(
    grouped: dict[str, list[Article]],
    hours: int,
    keywords: list[str] | None,
) -> str:
    """Format grouped articles as structured JSON."""
    sources = {}
    for source_key in SOURCE_ORDER:
        if source_key not in grouped:
            continue
        articles = grouped[source_key]
        sources[source_key] = {
            "display_name": SOURCE_DISPLAY_NAMES.get(source_key, source_key),
            "count": len(articles),
            "articles": [a.to_dict() for a in articles],
        }

    data = {
        "fetched_at": datetime.now(CST).isoformat(),
        "hours": hours,
        "keywords": keywords,
        "total_count": sum(len(a) for a in grouped.values()),
        "sources": sources,
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _format_metrics(metrics: dict) -> str:
    if not metrics:
        return ""
    parts = []
    if "views" in metrics:
        parts.append(f"👀 {_human_number(metrics['views'])}")
    if "likes" in metrics:
        parts.append(f"👍 {_human_number(metrics['likes'])}")
    if "comments" in metrics:
        parts.append(f"💬 {_human_number(metrics['comments'])}")
    if "reposts" in metrics:
        parts.append(f"🔄 {_human_number(metrics['reposts'])}")
    if not parts:
        return ""
    return " " + " ".join(parts)


def _human_number(n: int) -> str:
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)
