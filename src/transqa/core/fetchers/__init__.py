"""Web content fetchers for TransQA."""

from transqa.core.fetchers.base import BaseFetcher
from transqa.core.fetchers.requests_fetcher import RequestsFetcher
from transqa.core.fetchers.playwright_fetcher import PlaywrightFetcher
from transqa.core.fetchers.factory import FetcherFactory

__all__ = [
    "BaseFetcher",
    "RequestsFetcher", 
    "PlaywrightFetcher",
    "FetcherFactory",
]
