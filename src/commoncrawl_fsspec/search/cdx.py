"""CDX API search backend."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from requests import HTTPError

from ..constants import INDEX_BASE_URL
from ..models import SearchRecord
from ..clients.http_client import HttpClient
from .base import SearchBackend, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class CdxSearchBackend(SearchBackend):
    """Search backend using the Common Crawl CDX API."""

    def __init__(
        self, http_client: HttpClient, cdx_api_map: Optional[Dict[str, str]] = None
    ):
        self.http_client = http_client
        self.cdx_api_map = cdx_api_map or {}

    def _get_cdx_url(self, crawl_id: str) -> str:
        """Get the CDX API URL for a crawl."""
        if crawl_id in self.cdx_api_map and self.cdx_api_map[crawl_id]:
            return self.cdx_api_map[crawl_id]
        return f"{INDEX_BASE_URL}/{crawl_id}-index"

    def _search_hint(self, query: SearchQuery) -> str:
        return (
            "CDX search expects a URL pattern, not free text. "
            "Try something like '*.wikipedia.org/*' or 'https://en.wikipedia.org/*'. "
            f"Received: {query.url_pattern!r}."
        )

    def search(self, query: SearchQuery) -> SearchResult:
        """Search for records using CDX API."""
        cdx_url = self._get_cdx_url(query.crawl_id)

        params: Dict[str, Any] = {
            "url": query.url_pattern,
            "output": "json",
            "limit": query.limit,
        }

        if query.match_type:
            params["matchType"] = query.match_type

        if query.offset:
            params["offset"] = query.offset

        try:
            text = self.http_client.get_text(cdx_url, params=params)
        except HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                raise ValueError(self._search_hint(query)) from exc
            raise

        records = []
        total = 0

        for line in text.strip().split("\n"):
            if not line:
                continue
            try:
                record = json.loads(line)
                records.append(
                    SearchRecord(
                        urlkey=record.get("urlkey", ""),
                        timestamp=record.get("timestamp", ""),
                        url=record.get("url", ""),
                        mime=record.get("mime", ""),
                        status=record.get("status", ""),
                        digest=record.get("digest", ""),
                        length=int(record.get("length", 0)),
                        offset=int(record.get("offset", 0)),
                        filename=record.get("filename", ""),
                    )
                )
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse CDX line: {line[:100]}")

        return SearchResult(records=records, total=len(records))

    def count(self, query: SearchQuery) -> int:
        """Count records using CDX API."""
        cdx_url = self._get_cdx_url(query.crawl_id)

        params = {
            "url": query.url_pattern,
            "output": "json",
            "showNumPages": "true",
            "limit": 1,
        }

        try:
            text = self.http_client.get_text(cdx_url, params=params)
        except HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                raise ValueError(self._search_hint(query)) from exc
            raise

        if not text.strip():
            return 0

        try:
            record = json.loads(text.strip().split("\n")[0])
            if "numPages" in record:
                pages = int(record["numPages"])
                return pages * 1000  # CDX default page size
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

        return 0
