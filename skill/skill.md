---
name: news-digest
description: Fetch and summarize hot investment news from Chinese financial sources (华尔街见闻, 新浪财经, 雪球, 腾讯财经)
---

Fetch the latest investment news and provide a two-layer summary.

## Steps

1. Run the news fetcher with user's keywords (if any):

```bash
cd <skill-directory>/..
# If not installed yet:
pip install -e . 2>/dev/null

# Fetch news as JSON
cn-news-digest --json {{#if args}}--keywords "{{args}}"{{/if}}
```

2. Analyze the JSON output and produce a two-layer summary in Chinese:

**Layer 1: 今日投资要闻** (5-8 条)
- Merge coverage of the same event across different sources
- Rank by market impact and importance
- Each item: one-line headline + 1-2 sentence explanation of why it matters
- Flag if sources have divergent views on the same event

**Layer 2: 各源热点详情**
- Group by source (华尔街见闻 → 新浪财经 → 雪球 → 腾讯财经)
- For each source, list top articles with title, key takeaway, and link
- Note overall sentiment per source (偏多/偏空/中性)

## Output Format

```markdown
# 📰 投资要闻 (过去12小时)

## 核心事件

1. **事件标题** — 为什么重要，市场影响
2. ...

## 华尔街见闻
- **标题** — 要点 [链接](url)
- ...

## 新浪财经
...

## 雪球
...

## 腾讯财经
...

---
*数据来源：华尔街见闻、新浪财经、雪球、腾讯财经 | 抓取时间：YYYY-MM-DD HH:MM*
```
