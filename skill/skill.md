---
name: news-digest
description: Fetch and summarize hot investment news from Chinese financial sources (华尔街见闻, 新浪财经, 雪球, 腾讯财经)
---

Fetch the latest investment news and produce a daily digest.

## Steps

1. Run the news fetcher with user's keywords (if any):

```bash
cd <skill-directory>/..
# If not installed yet:
pip install -e . 2>/dev/null

# Fetch news as JSON
cn-news-digest --json --hours 24 --top 30 {{#if args}}--keywords "{{args}}"{{/if}}
```

2. Analyze the JSON output and produce a two-layer digest in Chinese:

**Layer 1: 核心事件** (5-8 条)
- Merge same event across sources into one entry
- Rank by market impact
- Each item: **bold headline** + one sentence why it matters + key data points
- NO links in this section
- Keep it tight: headline should be under 25 chars, explanation under 80 chars

**Layer 2: 各源详情**
- Group by source: 华尔街见闻 → 新浪财经 → 雪球 → 腾讯财经
- Each source: top articles as bullet list with title, one-line takeaway, [link](url), metrics
- End each source section with one-line sentiment tag (偏多/偏空/中性)

## Output Format

```markdown
# 投资要闻 (YYYY-MM-DD)

## 核心事件

1. **事件标题** — 一句话影响 + 关键数据
2. ...

## 华尔街见闻
- **标题** — 要点 [链接](url) 👀 阅读量
- ...
- 整体偏X，一句话总结

## 新浪财经
...

## 雪球
...

## 腾讯财经
...

---
*数据来源：华尔街见闻、新浪财经、雪球、腾讯财经 | 抓取时间：YYYY-MM-DD HH:MM*
```
