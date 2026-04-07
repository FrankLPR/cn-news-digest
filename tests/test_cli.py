import pytest
from unittest.mock import patch, AsyncMock
from click.testing import CliRunner
from datetime import datetime, timezone
from cn_news_digest.cli import main
from cn_news_digest.models import Article


@pytest.fixture
def mock_articles():
    return [
        Article(
            title="A股三大指数收涨",
            summary="今日A股三大指数集体收涨...",
            url="https://finance.sina.com.cn/001",
            source="sina",
            published_at=datetime(2026, 4, 7, 12, 0, tzinfo=timezone.utc),
            metrics={},
            tags=["A股"],
        ),
    ]


def test_cli_default_output(mock_articles):
    runner = CliRunner()
    with patch("cn_news_digest.cli.fetch_all", new_callable=AsyncMock, return_value=mock_articles):
        result = runner.invoke(main)
        assert result.exit_code == 0
        assert "投资要闻" in result.output
        assert "A股" in result.output


def test_cli_json_output(mock_articles):
    runner = CliRunner()
    with patch("cn_news_digest.cli.fetch_all", new_callable=AsyncMock, return_value=mock_articles):
        result = runner.invoke(main, ["--json"])
        assert result.exit_code == 0
        assert '"sources"' in result.output


def test_cli_keywords(mock_articles):
    runner = CliRunner()
    with patch("cn_news_digest.cli.fetch_all", new_callable=AsyncMock, return_value=mock_articles):
        result = runner.invoke(main, ["--keywords", "A股"])
        assert result.exit_code == 0
        assert "A股" in result.output


def test_cli_custom_hours(mock_articles):
    runner = CliRunner()
    with patch("cn_news_digest.cli.fetch_all", new_callable=AsyncMock, return_value=mock_articles) as mock_fetch:
        result = runner.invoke(main, ["--hours", "24"])
        assert result.exit_code == 0
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args
        assert call_kwargs[1]["hours"] == 24 or call_kwargs[0][0] == 24
