"""Caching utilities for Common Crawl fsspec plugin."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Optional

from .constants import MAX_RECORD_CACHE_SIZE
from .models import SearchRecord


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


class RecordCache:
    """LRU cache for search records."""

    def __init__(self, max_size: int = MAX_RECORD_CACHE_SIZE):
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()

    def get(self, key: str) -> Optional[SearchRecord]:
        """Get a record from the cache."""
        if key not in self._cache:
            return None

        self._cache.move_to_end(key)
        return self._cache[key]

    def put(self, key: str, value: SearchRecord) -> None:
        """Put a record in the cache."""
        if key in self._cache:
            self._cache.move_to_end(key)
        else:
            if len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
            self._cache[key] = value

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
