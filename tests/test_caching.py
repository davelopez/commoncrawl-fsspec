"""Tests for caching utilities."""

import time

from commoncrawl_fsspec.caching import CrawlListCache


class TestCrawlListCache:
    """Test CrawlListCache."""

    def test_put_and_get(self):
        cache = CrawlListCache(ttl=60)
        crawls = ["crawl1", "crawl2"]
        cache.put(crawls)
        assert cache.get() == crawls

    def test_expired_entry(self):
        cache = CrawlListCache(ttl=0.1)
        cache.put(["crawl1"])
        time.sleep(0.2)
        assert cache.get() is None

    def test_clear(self):
        cache = CrawlListCache()
        cache.put(["crawl1"])
        cache.clear()
        assert cache.get() is None
