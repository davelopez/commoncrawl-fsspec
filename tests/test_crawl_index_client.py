"""Tests for crawl index client."""

import responses

from commoncrawl_fsspec.clients.crawl_index_client import CrawlIndexClient
from commoncrawl_fsspec.clients.http_client import HttpClient
from commoncrawl_fsspec.constants import COLLINFO_URL


class TestCrawlIndexClient:
    """Test CrawlIndexClient."""

    @responses.activate
    def test_list_crawls(self):
        """Test fetching crawl list."""
        mock_data = [
            {
                "id": "CC-MAIN-2024-33",
                "name": "CC-MAIN-2024-33",
                "cdx_api": "https://index.commoncrawl.org/CC-MAIN-2024-33-index",
                "time_from": "20240801000000",
                "time_to": "20240831235959",
            },
            {
                "id": "CC-MAIN-2024-34",
                "name": "CC-MAIN-2024-34",
                "cdx_api": "https://index.commoncrawl.org/CC-MAIN-2024-34-index",
                "time_from": "20240901000000",
                "time_to": "20240930235959",
            },
        ]
        responses.add(responses.GET, COLLINFO_URL, json=mock_data, status=200)

        http_client = HttpClient()
        client = CrawlIndexClient(http_client)
        crawls = client.list_crawls()

        assert len(crawls) == 2
        assert crawls[0].id == "CC-MAIN-2024-33"
        assert crawls[0].name == "CC-MAIN-2024-33"
        assert crawls[1].id == "CC-MAIN-2024-34"

    @responses.activate
    def test_list_crawls_empty(self):
        """Test empty crawl list."""
        responses.add(responses.GET, COLLINFO_URL, json=[], status=200)

        http_client = HttpClient()
        client = CrawlIndexClient(http_client)
        crawls = client.list_crawls()

        assert len(crawls) == 0
