"""Crawl index client for fetching crawl metadata."""

from __future__ import annotations

import logging
from typing import List

from ..constants import COLLINFO_URL
from ..models import CrawlInfo
from .http_client import HttpClient

logger = logging.getLogger(__name__)


class CrawlIndexClient:
    """Client for fetching Common Crawl crawl list."""

    def __init__(self, http_client: HttpClient):
        self.http_client = http_client

    def list_crawls(self) -> List[CrawlInfo]:
        """Fetch and parse collinfo.json."""
        data = self.http_client.get_json(COLLINFO_URL)
        crawls = []
        for item in data:
            crawls.append(
                CrawlInfo(
                    id=item["id"],
                    name=item.get("name", ""),
                    time_from=item.get("time_from", ""),
                    time_to=item.get("time_to", ""),
                )
            )
        return crawls
