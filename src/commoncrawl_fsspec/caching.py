"""Caching utilities for Common Crawl fsspec plugin."""

from __future__ import annotations

import time
from typing import Optional


class CrawlListCache:
    """Cache for crawl list with TTL."""

    def __init__(self, ttl: int = 86400):
        self.ttl = ttl
        self._cache: Optional[tuple] = None

    def get(self) -> Optional[list]:
        """Get cached crawl list if it exists and is not expired."""
        if self._cache is None:
            return None

        crawls, expiry = self._cache
        if time.time() > expiry:
            self._cache = None
            return None

        return crawls

    def put(self, crawls: list) -> None:
        """Cache the crawl list."""
        self._cache = (crawls, time.time() + self.ttl)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache = None
