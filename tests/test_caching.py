"""Tests for caching utilities."""

import time
from commoncrawl_fsspec.caching import TTLCache, CrawlListCache, RecordCache
from commoncrawl_fsspec.models import SearchRecord


class TestTTLCache:
    """Test TTLCache."""

    def test_put_and_get(self):
        cache = TTLCache(ttl=60)
        cache.put("key", "value")
        assert cache.get("key") == "value"

    def test_expired_entry(self):
        cache = TTLCache(ttl=0.1)
        cache.put("key", "value")
        time.sleep(0.2)
        assert cache.get("key") is None

    def test_missing_key(self):
        cache = TTLCache()
        assert cache.get("missing") is None

    def test_clear(self):
        cache = TTLCache()
        cache.put("key", "value")
        cache.clear()
        assert cache.get("key") is None

    def test_max_size_eviction(self):
        cache = TTLCache(max_size=2)
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.put("key3", "value3")
        assert cache.get("key1") is None


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


class TestRecordCache:
    """Test RecordCache."""

    def test_put_and_get(self):
        cache = RecordCache()
        record = SearchRecord(
            urlkey="test",
            timestamp="20240101",
            url="http://example.com",
            mime="text/html",
            status="200",
            digest="abc123",
            length=100,
            offset=0,
            filename="test.warc.gz",
        )
        cache.put("token1", record)
        assert cache.get("token1") == record

    def test_missing_key(self):
        cache = RecordCache()
        assert cache.get("missing") is None

    def test_lru_eviction(self):
        cache = RecordCache(max_size=2)
        record1 = SearchRecord(
            urlkey="1",
            timestamp="20240101",
            url="http://1.com",
            mime="text/html",
            status="200",
            digest="a",
            length=10,
            offset=0,
            filename="1.warc.gz",
        )
        record2 = SearchRecord(
            urlkey="2",
            timestamp="20240102",
            url="http://2.com",
            mime="text/html",
            status="200",
            digest="b",
            length=20,
            offset=0,
            filename="2.warc.gz",
        )
        record3 = SearchRecord(
            urlkey="3",
            timestamp="20240103",
            url="http://3.com",
            mime="text/html",
            status="200",
            digest="c",
            length=30,
            offset=0,
            filename="3.warc.gz",
        )
        cache.put("token1", record1)
        cache.put("token2", record2)
        cache.put("token3", record3)
        assert cache.get("token1") is None
        assert cache.get("token2") == record2
        assert cache.get("token3") == record3

    def test_clear(self):
        cache = RecordCache()
        record = SearchRecord(
            urlkey="test",
            timestamp="20240101",
            url="http://example.com",
            mime="text/html",
            status="200",
            digest="abc",
            length=10,
            offset=0,
            filename="test.warc.gz",
        )
        cache.put("token", record)
        cache.clear()
        assert cache.get("token") is None
