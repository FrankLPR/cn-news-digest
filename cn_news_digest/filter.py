from __future__ import annotations

from cn_news_digest.models import Article

# Investment-related keywords for filtering non-investment content
INVESTMENT_KEYWORDS = {
    # Markets
    "股票", "股市", "A股", "美股", "港股", "股价", "涨停", "跌停", "牛市", "熊市",
    "大盘", "指数", "上证", "深证", "创业板", "科创板", "恒指", "纳指", "标普",
    "道琼斯", "两市", "沪深", "北向资金", "南向资金",
    # Instruments
    "基金", "ETF", "债券", "期货", "期权", "外汇", "黄金", "原油", "大宗商品",
    # Corporate
    "财报", "营收", "净利润", "毛利", "分红", "回购", "减持", "增持", "IPO",
    "并购", "重组", "定增", "配股", "解禁",
    # Macro
    "央行", "美联储", "降息", "加息", "降准", "利率", "通胀", "GDP", "CPI", "PMI",
    "货币政策", "财政政策", "汇率",
    # Valuation
    "估值", "市盈率", "市值", "PE", "PB", "ROE",
    # Sectors (common investment-relevant)
    "半导体", "芯片", "新能源", "光伏", "锂电", "算力", "AI芯片",
    # Economy & policy
    "经济增长", "产业链", "供应链", "外汇储备", "贸易战", "关税", "制裁",
    "房价", "楼市", "房贷",
    "出口", "进口",
    # Additional corporate/market terms
    "上市", "退市", "募股", "招股", "融资", "风投", "私募",
    "收购", "出售", "破产", "违约",
}

# Blacklist: articles matching these are definitely not investment content
NON_INVESTMENT_KEYWORDS = {
    "娱乐", "体育", "世界杯", "演唱会", "综艺", "电影", "电视剧",
    "明星", "八卦", "选秀", "真人秀",
    "食谱", "美食", "旅游", "景点",
    "渔民", "捕鱼", "金枪鱼",
    "心梗去世", "车祸", "地震",
}

# Sources that are dedicated finance channels (higher trust for investment relevance)
FINANCE_SOURCES = {"wallstreetcn", "sina", "xueqiu"}


def filter_articles(
    articles: list[Article],
    keywords: list[str] | None = None,
) -> list[Article]:
    """Filter articles to investment-related content, optionally by user keywords.

    1. Always applies investment relevance filter (title + summary + tags)
    2. If keywords provided, further filters to only articles matching any keyword
    """
    result = []
    for article in articles:
        if not _is_investment_related(article):
            continue
        if keywords and not _matches_keywords(article, keywords):
            continue
        result.append(article)
    return result


def _is_investment_related(article: Article) -> bool:
    """Check if article is related to investment/finance."""
    text = f"{article.title} {article.summary}".lower()

    # Blacklist check: reject if any non-investment keyword matches
    for kw in NON_INVESTMENT_KEYWORDS:
        if kw.lower() in text:
            return False

    # Count investment keyword hits
    hit_count = 0
    for kw in INVESTMENT_KEYWORDS:
        if kw.lower() in text:
            hit_count += 1
    # Also check tags
    for tag in article.tags:
        if tag in INVESTMENT_KEYWORDS:
            hit_count += 1

    if hit_count == 0:
        return False

    # For non-finance sources (e.g. tencent general hot list), require ≥2 hits
    # to avoid false positives like "总市值超10万" in fishing news
    if article.source not in FINANCE_SOURCES and hit_count < 2:
        return False

    return True


def _matches_keywords(article: Article, keywords: list[str]) -> bool:
    """Check if article matches any of the user-provided keywords."""
    text = f"{article.title} {article.summary}".lower()
    for kw in keywords:
        if kw.lower() in text:
            return True
    return False
