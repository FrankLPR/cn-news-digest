import json
import pytest
from datetime import datetime, timedelta
from cn_news_digest.models import Article, CST
from cn_news_digest.formatter import format_markdown, format_json


@pytest.fixture
def grouped_articles():
    now = datetime.now(CST) - timedelta(hours=1)
    return {
        "wallstreetcn": [
            Article(
                title="美联储维持利率不变",
                summary="美联储周三宣布维持联邦基金利率...",
                url="https://wallstreetcn.com/articles/123",
                source="wallstreetcn",
                published_at=now,
                metrics={"views": 50000, "comments": 320},
                tags=["美联储"],
            ),
        ],
        "xueqiu": [
            Article(
                title="为什么我重仓英伟达",
                summary="英伟达作为AI基础设施核心...",
                url="https://xueqiu.com/123/456",
                source="xueqiu",
                published_at=now,
                metrics={"likes": 2000, "comments": 450},
                tags=["英伟达", "AI"],
            ),
        ],
    }


def test_format_markdown_has_header(grouped_articles):
    md = format_markdown(grouped_articles)
    assert "投资要闻" in md


def test_format_markdown_has_source_sections(grouped_articles):
    md = format_markdown(grouped_articles)
    assert "华尔街见闻" in md
    assert "雪球" in md


def test_format_markdown_has_article_titles(grouped_articles):
    md = format_markdown(grouped_articles)
    assert "美联储维持利率不变" in md
    assert "为什么我重仓英伟达" in md


def test_format_markdown_has_links(grouped_articles):
    md = format_markdown(grouped_articles)
    assert "wallstreetcn.com" in md
    assert "xueqiu.com" in md


def test_format_markdown_has_metrics(grouped_articles):
    md = format_markdown(grouped_articles)
    assert "50000" in md or "5万" in md or "5.0万" in md or "50,000" in md


def test_format_json_structure(grouped_articles):
    output = format_json(grouped_articles, hours=12, keywords=None)
    data = json.loads(output)
    assert "fetched_at" in data
    assert "sources" in data
    assert "wallstreetcn" in data["sources"]
    assert data["sources"]["wallstreetcn"]["count"] == 1
    assert len(data["sources"]["wallstreetcn"]["articles"]) == 1


def test_format_json_with_keywords(grouped_articles):
    output = format_json(grouped_articles, hours=12, keywords=["英伟达"])
    data = json.loads(output)
    assert data["keywords"] == ["英伟达"]


def test_format_markdown_empty():
    md = format_markdown({})
    assert "没有找到" in md or "0" in md


def test_format_json_empty():
    output = format_json({}, hours=12, keywords=None)
    data = json.loads(output)
    assert data["sources"] == {}
