"""Common Crawl fsspec filesystem implementation."""

from __future__ import annotations

import logging

from fsspec import AbstractFileSystem

from .caching import CrawlListCache
from .clients.crawl_index_client import CrawlIndexClient
from .clients.http_client import HttpClient
from .clients.s3_listing_client import S3ListingClient
from .clients.warc_fetcher import WarcRecordFetcher
from .constants import DEFAULT_CACHE_TTL
from .paths import PathKind, PathResolver

logger = logging.getLogger(__name__)


class CommonCrawlFileSystem(AbstractFileSystem):
    """fsspec filesystem for Common Crawl.

    Protocol: cc
    """

    protocol = ("cc", "commoncrawl")
    root_marker = ""
    cachable = True

    def __init__(
        self,
        cache_ttl: int = DEFAULT_CACHE_TTL,
        **storage_options,
    ):
        """Initialize the Common Crawl filesystem.

        Args:
            cache_ttl: Cache TTL in seconds
            **storage_options: Additional storage options passed to AbstractFileSystem
        """
        super().__init__(**storage_options)

        self.http_client = HttpClient()
        self.crawl_index_client = CrawlIndexClient(self.http_client)
        self.s3_listing_client = S3ListingClient(http_client=self.http_client)
        self.warc_fetcher = WarcRecordFetcher(self.http_client)

        self.crawl_list_cache = CrawlListCache(ttl=cache_ttl)

    def _get_crawl_list(self) -> list:
        """Get the list of crawls, using cache if available."""
        cached = self.crawl_list_cache.get()
        if cached is not None:
            return cached

        crawls = self.crawl_index_client.list_crawls()
        self.crawl_list_cache.put(crawls)

        return crawls

    def ls(self, path, detail=True, **kwargs):
        """List directory contents."""
        vp = PathResolver.parse(path)

        if vp.kind == PathKind.ROOT:
            entries = [
                {"name": "/crawls", "type": "directory"},
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
            files = self.s3_listing_client.list_files(vp.crawl_id, vp.segment_id, vp.file_type)
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

        raise FileNotFoundError(path)

    def _open(self, path, mode="rb", **kwargs):
        """Open a file."""
        if mode != "rb":
            raise NotImplementedError("Common Crawl filesystem is read-only")

        vp = PathResolver.parse(path)

        if vp.kind == PathKind.WARC_FILE:
            return self.s3_listing_client.open(vp.to_s3_key(), mode)

        raise FileNotFoundError(path)

    def cat_file(self, path, start=0, end=None, **kwargs):
        """Read bytes from a file."""
        vp = PathResolver.parse(path)

        if vp.kind == PathKind.WARC_FILE:
            return self.s3_listing_client.cat_file(vp.to_s3_key(), start, end)

        raise FileNotFoundError(path)

    def get_file(self, rpath, lpath, **kwargs):
        """Get a file from the remote filesystem."""
        vp = PathResolver.parse(rpath)

        if vp.kind == PathKind.WARC_FILE:
            self.s3_listing_client.get_file(vp.to_s3_key(), lpath)
        else:
            raise FileNotFoundError(rpath)

    def invalidate_cache(self, path=None) -> None:
        """Invalidate the cache."""
        super().invalidate_cache(path)
        if path is None:
            self.crawl_list_cache.clear()

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
