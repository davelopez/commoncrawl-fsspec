"""Data models for Common Crawl fsspec plugin."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class EntryType(str, Enum):
    """Entry types for filesystem listings."""

    DIRECTORY = "directory"
    FILE = "file"


@dataclass(frozen=True)
class CrawlInfo:
    """Metadata about a Common Crawl crawl."""

    id: str
    name: str
    cdx_api: str
    time_from: str
    time_to: str


@dataclass(frozen=True)
class WarcFileInfo:
    """Metadata about a WARC file in S3."""

    name: str
    size: int
    last_modified: Optional[float] = None


@dataclass(frozen=True)
class SearchRecord:
    """A single search result record from Common Crawl."""

    urlkey: str
    timestamp: str
    url: str
    mime: str
    status: str
    digest: str
    length: int
    offset: int
    filename: str


@dataclass(frozen=True)
class FsEntry:
    """A filesystem entry returned by ls/info."""

    name: str
    type: EntryType
    size: int = 0
    mtime: Optional[float] = None
