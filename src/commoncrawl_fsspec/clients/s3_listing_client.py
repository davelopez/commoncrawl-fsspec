"""Listing and file access client for Common Crawl crawl-data manifests."""

from __future__ import annotations

import gzip
import io
import logging
from collections import OrderedDict
from email.utils import parsedate_to_datetime
from typing import List, Optional, Tuple

import fsspec
import requests

from ..constants import DATA_BASE_URL
from ..models import WarcFileInfo
from .http_client import HttpClient

logger = logging.getLogger(__name__)

MAX_MANIFEST_CACHE_ENTRIES = 16
MAX_DECOMPRESSED_MANIFEST_SIZE = 512 * 1024 * 1024  # 512 MB


class S3ListingClient:
    """Client for browsing Common Crawl crawl-data files."""

    def __init__(self, http_client: Optional[HttpClient] = None):
        self.http_client = http_client or HttpClient()
        self._http_fs = None
        self._manifest_cache: OrderedDict[Tuple[str, str], List[str]] = OrderedDict()

    @property
    def http_fs(self):
        """Lazy initialization of the HTTP filesystem."""
        if self._http_fs is None:
            self._http_fs = fsspec.filesystem("http")
        return self._http_fs

    def _manifest_url(self, crawl_id: str, file_type: str) -> str:
        return f"{DATA_BASE_URL}/crawl-data/{crawl_id}/{file_type}.paths.gz"

    def _load_manifest(self, crawl_id: str, file_type: str) -> List[str]:
        key = (crawl_id, file_type)
        cached = self._manifest_cache.get(key)
        if cached is not None:
            self._manifest_cache.move_to_end(key)
            return cached

        raw = self.http_client.get_bytes(self._manifest_url(crawl_id, file_type))
        chunks: List[bytes] = []
        total_size = 0
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
            while True:
                chunk = gz.read(65536)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_DECOMPRESSED_MANIFEST_SIZE:
                    raise ValueError(
                        f"Decompressed manifest exceeds {MAX_DECOMPRESSED_MANIFEST_SIZE} bytes"
                    )
                chunks.append(chunk)
        decompressed = b"".join(chunks)
        paths = [line.strip() for line in decompressed.decode("utf-8").splitlines()]
        paths = [path for path in paths if path]

        self._manifest_cache[key] = paths
        self._manifest_cache.move_to_end(key)
        while len(self._manifest_cache) > MAX_MANIFEST_CACHE_ENTRIES:
            self._manifest_cache.popitem(last=False)
        return paths

    def _iter_files(self, crawl_id: str, segment_id: str, file_type: str) -> List[str]:
        manifest_paths = self._load_manifest(crawl_id, file_type)
        prefix = f"crawl-data/{crawl_id}/segments/{segment_id}/{file_type}/"
        return [path for path in manifest_paths if path.startswith(prefix)]

    def _iter_segments(self, crawl_id: str) -> List[str]:
        manifest_paths = self._load_manifest(crawl_id, "warc")
        prefix = f"crawl-data/{crawl_id}/segments/"
        segments = set()
        for path in manifest_paths:
            if not path.startswith(prefix):
                continue
            parts = path.split("/")
            if len(parts) >= 5:
                segments.add(parts[3])
        return sorted(segments)

    def list_segments(self, crawl_id: str) -> List[WarcFileInfo]:
        """List segments for a crawl via the warc.paths.gz manifest."""
        return [
            WarcFileInfo(name=segment_id, size=0) for segment_id in self._iter_segments(crawl_id)
        ]

    def list_files(self, crawl_id: str, segment_id: str, file_type: str) -> List[WarcFileInfo]:
        """List files within a segment's file-type directory via manifest.

        Returns entries with size=0 and last_modified=None. Use get_file_info()
        for exact metadata on a specific file.
        """
        return [
            WarcFileInfo(name=path.rsplit("/", 1)[-1], size=0, last_modified=None)
            for path in self._iter_files(crawl_id, segment_id, file_type)
        ]

    def get_file_info(self, s3_key: str) -> Optional[dict]:
        """Get info for a single Common Crawl object."""
        try:
            resp = self.http_client.head(f"{DATA_BASE_URL}/{s3_key}")
            last_modified = resp.headers.get("Last-Modified")
            return {
                "Name": s3_key.split("/")[-1],
                "Size": int(resp.headers.get("Content-Length", 0)),
                "LastModified": (parsedate_to_datetime(last_modified) if last_modified else None),
            }
        except (requests.HTTPError, requests.ConnectionError, requests.Timeout) as exc:
            logger.warning("Failed to get file info for %s: %s", s3_key, exc)
            return None

    def open(self, s3_key: str, mode: str = "rb") -> object:
        """Open a Common Crawl object for reading."""
        return self.http_fs.open(f"{DATA_BASE_URL}/{s3_key}", mode)

    def get_file(self, rpath: str, lpath: str) -> None:
        """Download a Common Crawl object to a local path."""
        self.http_fs.get_file(f"{DATA_BASE_URL}/{rpath}", lpath)

    def cat_file(self, s3_key: str, start: int = 0, end: Optional[int] = None) -> bytes:
        """Read bytes from a Common Crawl object."""
        if end is None:
            return self.http_fs.cat(f"{DATA_BASE_URL}/{s3_key}", start=start)
        return self.http_fs.cat(f"{DATA_BASE_URL}/{s3_key}", start=start, end=end)
