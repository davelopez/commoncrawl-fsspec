"""Caching utilities for Common Crawl fsspec plugin."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Dict, Generic, Optional, TypeVar

from .models import CrawlInfo, SearchRecord

T = TypeVar("T")


class TTLCache(Generic[T]):
    """Simple TTL-based cache."""

    def __init__(self, ttl: int = 86400, max_size: int = 1000):
        self.ttl = ttl
        self.max_size = max_size
        self._cache: Dict[str, tuple] = {}

    def get(self, key: str) -> Optional[T]:
        """Get a value from the cache if it exists and is not expired."""
        if key not in self._cache:
            return None

        value, expiry = self._cache[key]
        if time.time() > expiry:
            del self._cache[key]
            return None

        return value

    def put(self, key: str, value: T) -> None:
        """Put a value in the cache."""
        if len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = (value, time.time() + self.ttl)

    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()


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

    def __init__(self, max_size: int = 10000):
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
