"""Data models for Common Crawl fsspec plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CrawlInfo:
    """Metadata about a Common Crawl crawl."""

    id: str
    name: str
    time_from: str
    time_to: str


@dataclass(frozen=True)
class WarcFileInfo:
    """Metadata about a WARC file in S3."""

    name: str
    size: int
    last_modified: Optional[float] = None
