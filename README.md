# cn-news-digest

Fetch and summarize hot investment news from Chinese financial sources.

## Sources

- 华尔街见闻 (Wall Street CN)
- 腾讯财经 (Tencent Finance)
- 新浪财经 (Sina Finance)
- 雪球 (Xueqiu)

## Install

```bash
pip install cn-news-digest
```

## Usage

```bash
# Fetch all investment news from past 12 hours
cn-news-digest

# Filter by keywords
cn-news-digest --keywords "英伟达,AI"

# JSON output
cn-news-digest --json

# Custom time range
cn-news-digest --hours 24 --top 20
```

## Library Usage

```python
import asyncio
from cn_news_digest import fetch_all, filter_articles, aggregate, format_markdown

async def main():
    articles = await fetch_all(hours=12, top_n=15)
    filtered = filter_articles(articles, keywords=["英伟达", "AI"])
    grouped = aggregate(filtered)
    print(format_markdown(grouped))

asyncio.run(main())
```

## Claude Code Skill

Copy `skill/` to your Claude Code skills directory:

```bash
cp -r skill/ ~/.claude/skills/news-digest/
```

Then use `/news-digest` or `/news-digest 英伟达 AI` in Claude Code.

## Configuration

Zero config required. Optional:

- `RSSHUB_URL` — custom RSSHub instance (default: `https://rsshub.app`)

## Author

[Frank Xu](https://github.com/FrankLPR)
