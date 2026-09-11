"""WARC record fetcher using HTTP byte ranges."""

from __future__ import annotations

import io
import logging

from ..constants import DATA_BASE_URL
from .http_client import HttpClient

logger = logging.getLogger(__name__)


class WarcRecordFetcher:
    """Fetch WARC records using HTTP byte-range requests."""

    def __init__(self, http_client: HttpClient):
        self.http_client = http_client

    def fetch_record(self, filename: str, offset: int, length: int) -> bytes:
        """Fetch a WARC record using HTTP byte range."""
        url = f"{DATA_BASE_URL}/{filename}"
        return self.http_client.get_range(url, offset, offset + length)

    def fetch_record_stream(
        self, filename: str, offset: int, length: int
    ) -> io.BytesIO:
        """Fetch a WARC record and return as a BytesIO stream."""
        data = self.fetch_record(filename, offset, length)
        return io.BytesIO(data)
