"""News source fetchers."""

from cn_news_digest.sources.wallstreetcn import WallStreetCNSource
from cn_news_digest.sources.xueqiu import XueqiuSource
from cn_news_digest.sources.sina import SinaFinanceSource
from cn_news_digest.sources.tencent import TencentFinanceSource

ALL_SOURCES = [
    WallStreetCNSource,
    XueqiuSource,
    SinaFinanceSource,
    TencentFinanceSource,
]

__all__ = [
    "ALL_SOURCES",
    "WallStreetCNSource",
    "XueqiuSource",
    "SinaFinanceSource",
    "TencentFinanceSource",
]
