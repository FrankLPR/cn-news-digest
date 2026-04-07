# cn-news-digest

从中国主流财经媒体抓取过去 12 小时的投资热点新闻，零配置开箱即用。
Author: Frank Xu

## 数据源

| 源 | 抓取方式 | 数据类型 |
|---|---|---|
| 华尔街见闻 | RSSHub → Direct API (`api-one-wscn.awtmt.com`) | 热门文章 + 7x24 快讯 |
| 新浪财经 | RSSHub → Direct API (`feed.mix.sina.com.cn`) | 财经滚动新闻 |
| 雪球 | RSSHub → Playwright 拦截 XHR (`hot_event/list.json`) | 热门话题 |
| 腾讯财经 | Direct API (`i.news.qq.com/gw/event/pc_hot_ranking_list`) | 通用热榜（投资过滤） |

**抓取策略：** RSSHub 优先（默认公共实例 `rsshub.app`），失败时自动 fallback 到直接 API。雪球因阿里云 WAF 防护，fallback 使用 Playwright 在浏览器上下文内拦截页面加载时的 XHR 响应。

### 雪球端点说明

雪球所有 API 均受阿里云 WAF 保护，简单 HTTP 请求无法获取有效 `xq_a_token` cookie。解决方案：

1. **RSSHub**（优先）：RSSHub 内部用 Puppeteer 解决 WAF 验证
2. **Playwright fallback**：启动 headless Chromium 访问 `https://xueqiu.com`，拦截页面加载时自动发出的 `https://xueqiu.com/hot_event/list.json` XHR 响应，获取热门话题数据（10 条，含 tag/content/讨论数）

数据结构：
```json
{
  "list": [
    {
      "id": 469829,
      "tag": "#算力芯片概念反弹，寒武纪大涨#",
      "content": "算力芯片概念盘中持续反弹...",
      "status_count": 82,
      "hot": 1
    }
  ]
}
```

## 安装

```bash
# 基础安装（华尔街见闻 + 新浪 + 腾讯）
pip install cn-news-digest

# 完整安装（含雪球 Playwright 支持）
pip install 'cn-news-digest[browser]'
playwright install chromium
```

## 使用

### 命令行

```bash
# 默认：过去 12 小时投资新闻，Markdown 格式
cn-news-digest

# 关键词筛选（OR 逻辑，匹配标题+摘要）
cn-news-digest --keywords "英伟达,AI,半导体"

# JSON 输出（给程序用）
cn-news-digest --json

# 自定义时间范围和数量
cn-news-digest --hours 24 --top 20

# 自定义 RSSHub 实例
RSSHUB_URL=https://my-rsshub.com cn-news-digest
```

### Python 库

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

### Claude Code Skill

```bash
cp -r skill/ ~/.claude/skills/news-digest/
```

然后在 Claude Code 中：
```
/news-digest              # 全部投资新闻
/news-digest 英伟达 AI    # 按关键词筛选
```

Claude 会自动抓取数据并生成两层总结：核心事件（跨源聚合）+ 各源详细列表。

## 架构

```
cn-news-digest/
├── cn_news_digest/
│   ├── models.py          # Article 数据类
│   ├── rsshub.py          # RSSHub 客户端
│   ├── sources/
│   │   ├── base.py        # BaseSource 抽象基类
│   │   ├── wallstreetcn.py # RSSHub + api-one-wscn.awtmt.com (hot + lives)
│   │   ├── xueqiu.py      # RSSHub + Playwright XHR 拦截
│   │   ├── sina.py         # RSSHub + feed.mix.sina.com.cn
│   │   └── tencent.py      # pc_hot_ranking_list (直接 API)
│   ├── filter.py          # 投资关键词白名单 + 黑名单 + 用户关键词
│   ├── aggregator.py      # 模糊去重 + 按源分组
│   ├── formatter.py       # Markdown / JSON 输出
│   └── cli.py             # Click CLI
├── skill/
│   └── skill.md           # Claude Code skill
├── tests/                 # 55 个测试
├── pyproject.toml
└── README.md
```

数据流：
```
4 源并发抓取 → 投资相关过滤 → 关键词筛选 → 模糊去重 → 按源分组 → 格式化输出
```

## 过滤逻辑

1. **投资白名单**（80+ 词）：股票/基金/央行/财报/IPO/并购/ETF/利率/降息...
2. **噪音黑名单**：娱乐/体育/美食/旅游/社会新闻等
3. **用户关键词**（可选）：`--keywords` 指定，OR 逻辑，不区分大小写
4. **去重**：跨源标题 SequenceMatcher > 0.55，保留互动数据更多的版本

## 配置

零配置即可使用。可选：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RSSHUB_URL` | `https://rsshub.app` | 自定义 RSSHub 实例 |

## 依赖

| 包 | 用途 | 必需 |
|---|---|---|
| httpx | 异步 HTTP | 是 |
| feedparser | RSS 解析 | 是 |
| click | CLI | 是 |
| playwright | 雪球抓取 | 可选 (`[browser]`) |

## 开发

```bash
git clone <repo>
cd cn-news-digest
pip install -e ".[dev,browser]"
pytest tests/ -v   # 55 tests
```

## 已知限制

- **雪球** 需 Playwright + Chromium，每次抓取启动浏览器约 8-10 秒
- **腾讯** 使用通用热榜（专用财经排行数据过时），依赖过滤层筛选
- **RSSHub 公共实例** 可能限流，建议自部署
- 雪球热门话题无发布时间戳，使用抓取时间

## License

MIT
