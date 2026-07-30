"""Common Crawl fsspec filesystem implementation."""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List, Optional, Tuple

from fsspec import AbstractFileSystem

from .caching import CrawlListCache, RecordCache
from .clients.crawl_index_client import CrawlIndexClient
from .clients.http_client import HttpClient
from .clients.s3_listing_client import S3ListingClient
from .clients.warc_fetcher import WarcRecordFetcher
from .constants import (
    DEFAULT_CACHE_TTL,
    DEFAULT_MAX_SEARCH_RESULTS,
    S3_BUCKET,
)
from .models import EntryType, FsEntry, SearchRecord
from .paths import PathKind, PathResolver, VirtualPath
from .search.base import SearchBackend, SearchQuery, SearchResult
from .search.factory import create_search_backend

logger = logging.getLogger(__name__)


class CommonCrawlRecordFile(io.BytesIO):
    """File-like object for a WARC record fetched via HTTP byte range."""

    def __init__(
        self,
        fetcher: WarcRecordFetcher,
        filename: str,
        offset: int,
        length: int,
    ):
        super().__init__()
        self.fetcher = fetcher
        self.filename = filename
        self.offset = offset
        self.length = length
        self._fetched = False
        self._size = length

    def _ensure_fetched(self):
        if not self._fetched:
            data = self.fetcher.fetch_record(self.filename, self.offset, self.length)
            self.write(data)
            self.seek(0)
            self._fetched = True

    @property
    def size(self):
        return self._size

    def read(self, size=-1):
        self._ensure_fetched()
        return super().read(size)

    def seek(self, pos, whence=0):
        self._ensure_fetched()
        return super().seek(pos, whence)

    def tell(self):
        self._ensure_fetched()
        return super().tell()


class CommonCrawlFileSystem(AbstractFileSystem):
    """fsspec filesystem for Common Crawl.

    Protocol: cc
    """

    protocol = ("cc", "commoncrawl")
    root_marker = ""
    cachable = True

    def __init__(
        self,
        search_backend: str = "cdx",
        anon: bool = True,
        max_search_results: int = DEFAULT_MAX_SEARCH_RESULTS,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        **storage_options,
    ):
        """Initialize the Common Crawl filesystem.

        Args:
            search_backend: Search backend to use ("cdx" or "parquet")
            anon: Use anonymous S3 access
            max_search_results: Maximum number of search results to return
            cache_ttl: Cache TTL in seconds
            **storage_options: Additional storage options passed to AbstractFileSystem
        """
        super().__init__(**storage_options)

        self.http_client = HttpClient()
        self.crawl_index_client = CrawlIndexClient(self.http_client)
        self.s3_listing_client = S3ListingClient(
            anon=anon, http_client=self.http_client
        )
        self.warc_fetcher = WarcRecordFetcher(self.http_client)

        self.crawl_list_cache = CrawlListCache(ttl=cache_ttl)
        self.record_cache = RecordCache()

        self._cdx_api_map: dict[str, str] = {}
        self.search_backend: SearchBackend = create_search_backend(
            search_backend,
            self.http_client,
            cdx_api_map=self._cdx_api_map,
        )

        self.max_search_results = max_search_results

    def _get_crawl_list(self) -> list:
        """Get the list of crawls, using cache if available."""
        cached = self.crawl_list_cache.get()
        if cached is not None:
            return cached

        crawls = self.crawl_index_client.list_crawls()
        self.crawl_list_cache.put(crawls)

        for crawl in crawls:
            self._cdx_api_map[crawl.id] = crawl.cdx_api

        return crawls

    def ls(self, path, detail=True, **kwargs):
        """List directory contents."""
        vp = PathResolver.parse(path)

        if vp.kind == PathKind.ROOT:
            entries = [
                {"name": "/crawls", "type": "directory"},
                {"name": "/search", "type": "directory"},
            ]
        elif vp.kind == PathKind.CRAWLS:
            crawls = self._get_crawl_list()
            entries = [
                {
                    "name": PathResolver.build(PathKind.CRAWL, crawl_id=crawl.id),
                    "type": "directory",
                }
                for crawl in crawls
            ]
        elif vp.kind == PathKind.CRAWL:
            entries = [
                {
                    "name": PathResolver.build(PathKind.SEGMENTS, crawl_id=vp.crawl_id),
                    "type": "directory",
                }
            ]
        elif vp.kind == PathKind.SEGMENTS:
            segments = self.s3_listing_client.list_segments(vp.crawl_id)
            entries = [
                {
                    "name": PathResolver.build(
                        PathKind.SEGMENT, crawl_id=vp.crawl_id, segment_id=seg.name
                    ),
                    "type": "directory",
                }
                for seg in segments
            ]
        elif vp.kind == PathKind.SEGMENT:
            entries = [
                {
                    "name": PathResolver.build(
                        PathKind.FILE_TYPE,
                        crawl_id=vp.crawl_id,
                        segment_id=vp.segment_id,
                        file_type=ft,
                    ),
                    "type": "directory",
                }
                for ft in ("warc", "wet", "wat")
            ]
        elif vp.kind == PathKind.FILE_TYPE:
            files = self.s3_listing_client.list_files(
                vp.crawl_id, vp.segment_id, vp.file_type
            )
            entries = [
                {
                    "name": PathResolver.build(
                        PathKind.WARC_FILE,
                        crawl_id=vp.crawl_id,
                        segment_id=vp.segment_id,
                        file_type=vp.file_type,
                        filename=f.name,
                    ),
                    "type": "file",
                    "size": f.size,
                    "mtime": f.last_modified,
                }
                for f in files
            ]
        elif vp.kind == PathKind.SEARCH:
            crawls = self._get_crawl_list()
            entries = [
                {
                    "name": PathResolver.build(
                        PathKind.SEARCH_CRAWL, crawl_id=crawl.id
                    ),
                    "type": "directory",
                }
                for crawl in crawls
            ]
        elif vp.kind == PathKind.SEARCH_CRAWL:
            entries = []
        else:
            entries = []

        if detail:
            return entries
        return [e["name"] for e in entries]

    def info(self, path):
        """Get info about a path."""
        vp = PathResolver.parse(path)

        if vp.kind in (
            PathKind.ROOT,
            PathKind.CRAWLS,
            PathKind.CRAWL,
            PathKind.SEGMENTS,
            PathKind.SEGMENT,
            PathKind.FILE_TYPE,
            PathKind.SEARCH,
            PathKind.SEARCH_CRAWL,
        ):
            return {"name": path, "type": "directory"}
        elif vp.kind == PathKind.WARC_FILE:
            s3_key = vp.to_s3_key()
            info = self.s3_listing_client.get_file_info(s3_key)
            if info:
                return {
                    "name": path,
                    "type": "file",
                    "size": info["Size"],
                    "mtime": info["LastModified"].timestamp(),
                }
            return {"name": path, "type": "file", "size": 0}
        elif vp.kind == PathKind.RECORD:
            record = self.record_cache.get(vp.record_token)
            if record:
                return {
                    "name": path,
                    "type": "file",
                    "size": record.length,
                    "url": record.url,
                    "timestamp": record.timestamp,
                }
            return {
                "name": path,
                "type": "file",
                "size": 0,
            }

        raise FileNotFoundError(path)

    def glob(self, pattern, detail=True, **kwargs):
        """Glob for files matching a pattern."""
        vp = PathResolver.parse(pattern.split("*")[0])

        if vp.kind == PathKind.SEARCH_CRAWL:
            query_part = pattern.split("*")[1].split("*")[-1] if "*" in pattern else ""
            if not query_part:
                return []

            search_query = SearchQuery(
                crawl_id=vp.crawl_id,
                url_pattern=f"%{query_part}%",
                limit=self.max_search_results,
            )

            result = self.search_backend.search(search_query)

            entries = []
            for record in result.records:
                token = PathResolver.encode_record_token(
                    record.filename, record.offset, record.length
                )
                self.record_cache.put(token, record)
                record_path = PathResolver.build(
                    PathKind.RECORD, crawl_id=vp.crawl_id, record_token=token
                )
                entries.append(
                    {
                        "name": record_path,
                        "type": "file",
                        "size": record.length,
                        "url": record.url,
                        "timestamp": record.timestamp,
                    }
                )

            if detail:
                return entries
            return [e["name"] for e in entries]

        return super().glob(pattern, detail=detail, **kwargs)

    def _open(self, path, mode="rb", **kwargs):
        """Open a file."""
        if mode != "rb":
            raise NotImplementedError("Common Crawl filesystem is read-only")

        vp = PathResolver.parse(path)

        if vp.kind == PathKind.WARC_FILE:
            return self.s3_listing_client.open(vp.to_s3_key(), mode)
        elif vp.kind == PathKind.RECORD:
            filename, offset, length = PathResolver.decode_record_token(vp.record_token)
            return CommonCrawlRecordFile(self.warc_fetcher, filename, offset, length)

        raise FileNotFoundError(path)

    def cat_file(self, path, start=0, end=None, **kwargs):
        """Read bytes from a file."""
        vp = PathResolver.parse(path)

        if vp.kind == PathKind.WARC_FILE:
            return self.s3_listing_client.cat_file(vp.to_s3_key(), start, end)
        elif vp.kind == PathKind.RECORD:
            filename, offset, length = PathResolver.decode_record_token(vp.record_token)
            actual_start = offset + start
            actual_end = min(
                offset + length, end if end is not None else offset + length
            )
            return self.warc_fetcher.fetch_record(
                filename, actual_start, actual_end - actual_start
            )

        raise FileNotFoundError(path)

    def get_file(self, rpath, lpath, **kwargs):
        """Get a file from the remote filesystem."""
        vp = PathResolver.parse(rpath)

        if vp.kind == PathKind.WARC_FILE:
            self.s3_listing_client.get_file(vp.to_s3_key(), lpath)
        elif vp.kind == PathKind.RECORD:
            filename, offset, length = PathResolver.decode_record_token(vp.record_token)
            data = self.warc_fetcher.fetch_record(filename, offset, length)
            with open(lpath, "wb") as f:
                f.write(data)
        else:
            raise FileNotFoundError(rpath)

    def invalidate_cache(self, path=None) -> None:
        """Invalidate the cache."""
        super().invalidate_cache(path)
        if path is None:
            self.crawl_list_cache.clear()
            self.record_cache.clear()

    def rm(self, path, **kwargs):
        """Remove a file (not supported)."""
        raise NotImplementedError("Common Crawl filesystem is read-only")

    def mkdir(self, path, **kwargs):
        """Create a directory (not supported)."""
        raise NotImplementedError("Common Crawl filesystem is read-only")

    def rmdir(self, path, **kwargs):
        """Remove a directory (not supported)."""
        raise NotImplementedError("Common Crawl filesystem is read-only")

    def mv(self, path1, path2, **kwargs):
        """Move a file (not supported)."""
        raise NotImplementedError("Common Crawl filesystem is read-only")

    def copy(self, path1, path2, **kwargs):
        """Copy a file (not supported)."""
        raise NotImplementedError("Common Crawl filesystem is read-only")

    def pipe_file(self, path, value, **kwargs):
        """Write to a file (not supported)."""
        raise NotImplementedError("Common Crawl filesystem is read-only")

    def put_file(self, lpath, rpath, **kwargs):
        """Upload a file (not supported)."""
        raise NotImplementedError("Common Crawl filesystem is read-only")

    def upload_file(self, lpath, rpath, **kwargs):
        """Upload a file (not supported)."""
        raise NotImplementedError("Common Crawl filesystem is read-only")
