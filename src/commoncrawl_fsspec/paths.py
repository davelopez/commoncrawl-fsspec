"""Path parsing and building for Common Crawl virtual filesystem."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class PathKind(str, Enum):
    """Kinds of virtual paths."""

    ROOT = "root"
    CRAWLS = "crawls"
    CRAWL = "crawl"
    SEGMENTS = "segments"
    SEGMENT = "segment"
    FILE_TYPE = "file_type"
    WARC_FILE = "warc_file"
    SEARCH = "search"
    SEARCH_CRAWL = "search_crawl"
    RECORD = "record"


@dataclass(frozen=True)
class VirtualPath:
    """Parsed virtual path with kind and components."""

    kind: PathKind
    crawl_id: Optional[str] = None
    segment_id: Optional[str] = None
    file_type: Optional[str] = None
    filename: Optional[str] = None
    record_token: Optional[str] = None
    raw_path: str = ""


class PathResolver:
    """Parse and build virtual paths."""

    @staticmethod
    def parse(path: str) -> VirtualPath:
        """Parse a path string into a VirtualPath."""
        if path in ("/", ""):
            return VirtualPath(kind=PathKind.ROOT, raw_path=path)

        parts = path.strip("/").split("/")

        if parts[0] == "crawls":
            if len(parts) == 1:
                return VirtualPath(kind=PathKind.CRAWLS, raw_path=path)
            elif len(parts) == 2:
                return VirtualPath(
                    kind=PathKind.CRAWL, crawl_id=parts[1], raw_path=path
                )
            elif len(parts) == 3 and parts[2] == "segments":
                return VirtualPath(
                    kind=PathKind.SEGMENTS, crawl_id=parts[1], raw_path=path
                )
            elif len(parts) == 4:
                return VirtualPath(
                    kind=PathKind.SEGMENT,
                    crawl_id=parts[1],
                    segment_id=parts[3],
                    raw_path=path,
                )
            elif len(parts) == 5:
                return VirtualPath(
                    kind=PathKind.FILE_TYPE,
                    crawl_id=parts[1],
                    segment_id=parts[3],
                    file_type=parts[4],
                    raw_path=path,
                )
            elif len(parts) >= 6:
                filename = "/".join(parts[5:])
                return VirtualPath(
                    kind=PathKind.WARC_FILE,
                    crawl_id=parts[1],
                    segment_id=parts[3],
                    file_type=parts[4],
                    filename=filename,
                    raw_path=path,
                )

        if parts[0] == "search":
            if len(parts) == 1:
                return VirtualPath(kind=PathKind.SEARCH, raw_path=path)
            elif len(parts) == 2:
                return VirtualPath(
                    kind=PathKind.SEARCH_CRAWL, crawl_id=parts[1], raw_path=path
                )
            elif len(parts) == 3:
                return VirtualPath(
                    kind=PathKind.RECORD,
                    crawl_id=parts[1],
                    record_token=parts[2],
                    raw_path=path,
                )

        raise ValueError(f"Cannot parse path: {path}")

    @staticmethod
    def build(kind: PathKind, **kwargs) -> str:
        """Build a path string from components."""
        if kind == PathKind.ROOT:
            return "/"
        if kind == PathKind.CRAWLS:
            return "/crawls"
        if kind == PathKind.CRAWL:
            return f"/crawls/{kwargs['crawl_id']}"
        if kind == PathKind.SEGMENTS:
            return f"/crawls/{kwargs['crawl_id']}/segments"
        if kind == PathKind.SEGMENT:
            return f"/crawls/{kwargs['crawl_id']}/segments/{kwargs['segment_id']}"
        if kind == PathKind.FILE_TYPE:
            return f"/crawls/{kwargs['crawl_id']}/segments/{kwargs['segment_id']}/{kwargs['file_type']}"
        if kind == PathKind.WARC_FILE:
            return f"/crawls/{kwargs['crawl_id']}/segments/{kwargs['segment_id']}/{kwargs['file_type']}/{kwargs['filename']}"
        if kind == PathKind.SEARCH:
            return "/search"
        if kind == PathKind.SEARCH_CRAWL:
            return f"/search/{kwargs['crawl_id']}"
        if kind == PathKind.RECORD:
            return f"/search/{kwargs['crawl_id']}/{kwargs['record_token']}"
        raise ValueError(f"Cannot build path for kind: {kind}")

    @staticmethod
    def encode_record_token(filename: str, offset: int, length: int) -> str:
        """Encode a record token from filename, offset, and length."""
        raw = f"{filename}\n{offset}\n{length}"
        return base64.urlsafe_b64encode(raw.encode()).decode()

    @staticmethod
    def decode_record_token(token: str) -> Tuple[str, int, int]:
        """Decode a record token into (filename, offset, length)."""
        raw = base64.urlsafe_b64decode(token).decode()
        parts = raw.split("\n")
        return parts[0], int(parts[1]), int(parts[2])
