"""Tests for CDX search backend."""

import json
import pytest
import responses
from commoncrawl_fsspec.clients.http_client import HttpClient
from commoncrawl_fsspec.search.cdx import CdxSearchBackend
from commoncrawl_fsspec.search.base import SearchQuery


class TestCdxSearchBackend:
    """Test CdxSearchBackend."""

    @responses.activate
    def test_search(self):
        """Test CDX search."""
        cdx_url = "https://index.commoncrawl.org/CC-MAIN-2024-33-index"
        mock_ndjson = json.dumps(
            {
                "urlkey": "example.com",
                "timestamp": "20240801120000",
                "url": "http://example.com/page",
                "mime": "text/html",
                "status": "200",
                "digest": "abc123",
                "length": "1000",
                "offset": "5000",
                "filename": "CC-MAIN-2024.warc.gz",
            }
        )
        responses.add(responses.GET, cdx_url, body=mock_ndjson + "\n", status=200)

        http_client = HttpClient()
        backend = CdxSearchBackend(http_client)
        query = SearchQuery(
            crawl_id="CC-MAIN-2024-33",
            url_pattern="*example.com*",
            limit=10,
        )
        result = backend.search(query)

        assert len(result.records) == 1
        record = result.records[0]
        assert record.url == "http://example.com/page"
        assert record.filename == "CC-MAIN-2024.warc.gz"
        assert record.offset == 5000
        assert record.length == 1000

    @responses.activate
    def test_search_empty(self):
        """Test empty CDX search."""
        cdx_url = "https://index.commoncrawl.org/CC-MAIN-2024-33-index"
        responses.add(responses.GET, cdx_url, body="", status=200)

        http_client = HttpClient()
        backend = CdxSearchBackend(http_client)
        query = SearchQuery(
            crawl_id="CC-MAIN-2024-33",
            url_pattern="*nonexistent*",
            limit=10,
        )
        result = backend.search(query)

        assert len(result.records) == 0

    @responses.activate
    def test_count(self):
        """Test CDX count."""
        cdx_url = "https://index.commoncrawl.org/CC-MAIN-2024-33-index"
        mock_record = json.dumps(
            {
                "urlkey": "example.com",
                "numPages": 5,
            }
        )
        responses.add(responses.GET, cdx_url, body=mock_record + "\n", status=200)

        http_client = HttpClient()
        backend = CdxSearchBackend(http_client)
        query = SearchQuery(
            crawl_id="CC-MAIN-2024-33",
            url_pattern="*example.com*",
        )
        count = backend.count(query)

        assert count == 5000  # 5 pages * 1000 default page size

    @responses.activate
    def test_search_404_shows_hint(self):
        """Test that a CDX 404 raises a helpful search hint."""
        cdx_url = "https://index.commoncrawl.org/CC-MAIN-2024-33-index"
        responses.add(responses.GET, cdx_url, status=404)

        http_client = HttpClient()
        backend = CdxSearchBackend(http_client)
        query = SearchQuery(
            crawl_id="CC-MAIN-2024-33",
            url_pattern="wikipedia",
            limit=10,
        )

        with pytest.raises(ValueError, match="URL pattern"):
            backend.search(query)
