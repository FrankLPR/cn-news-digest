from __future__ import annotations

import asyncio

import click

from cn_news_digest.aggregator import aggregate
from cn_news_digest.filter import filter_articles
from cn_news_digest.formatter import format_json, format_markdown
from cn_news_digest.models import Article
from cn_news_digest.sources import ALL_SOURCES


async def fetch_all(hours: int = 12, top_n: int = 15) -> list[Article]:
    """Fetch articles from all sources concurrently."""
    sources = [cls() for cls in ALL_SOURCES]
    tasks = [source.fetch(hours=hours, top_n=top_n) for source in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    articles = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            source_name = sources[i].display_name
            click.echo(f"⚠ {source_name} 抓取失败: {result}", err=True)
            continue
        articles.extend(result)
    return articles


@click.command()
@click.option("--hours", default=12, help="抓取过去N小时的新闻 (默认12)")
@click.option("--top", "top_n", default=15, help="每个源取Top N条 (默认15)")
@click.option("--keywords", default=None, help="关键词过滤，逗号分隔 (如: 英伟达,AI)")
@click.option("--json", "output_json", is_flag=True, help="输出JSON格式")
def main(hours: int, top_n: int, keywords: str | None, output_json: bool):
    """抓取中国财经新闻源的投资热点新闻。"""
    keyword_list = [k.strip() for k in keywords.split(",") if k.strip()] if keywords else None

    articles = asyncio.run(fetch_all(hours=hours, top_n=top_n))
    filtered = filter_articles(articles, keywords=keyword_list)
    grouped = aggregate(filtered)

    if output_json:
        click.echo(format_json(grouped, hours=hours, keywords=keyword_list))
    else:
        click.echo(format_markdown(grouped))


if __name__ == "__main__":
    main()
