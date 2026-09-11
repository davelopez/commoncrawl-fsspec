"""Path parsing and building for Common Crawl virtual filesystem."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

VALID_FILE_TYPES = frozenset({"warc", "wet", "wat"})


def _validate_path_component(value: str, name: str) -> str:
    """Validate a path component is safe for URL/S3 key interpolation."""
    if not value or ".." in value or "//" in value:
        raise ValueError(f"Invalid {name}: {value!r}")
    return value


def _validate_file_type(value: str) -> str:
    """Validate file_type against the allowed set."""
    if value not in VALID_FILE_TYPES:
        raise ValueError(f"Invalid file_type: {value!r}. Must be one of {sorted(VALID_FILE_TYPES)}")
    return value


class PathKind(str, Enum):
    """Kinds of virtual paths."""

    ROOT = "root"
    CRAWLS = "crawls"
    CRAWL = "crawl"
    SEGMENTS = "segments"
    SEGMENT = "segment"
    FILE_TYPE = "file_type"
    WARC_FILE = "warc_file"


@dataclass(frozen=True)
class VirtualPath:
    """Parsed virtual path with kind and components."""

    kind: PathKind
    crawl_id: Optional[str] = None
    segment_id: Optional[str] = None
    file_type: Optional[str] = None
    filename: Optional[str] = None
    raw_path: str = ""

    def to_s3_prefix(self) -> str:
        """Build the S3 prefix for this path's file-type directory."""
        return f"crawl-data/{self.crawl_id}/segments/{self.segment_id}/{self.file_type}/"

    def to_s3_key(self) -> str:
        """Build the full S3 key for this path's WARC file."""
        return f"{self.to_s3_prefix()}{self.filename}"


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
                    kind=PathKind.CRAWL,
                    crawl_id=_validate_path_component(parts[1], "crawl_id"),
                    raw_path=path,
                )
            elif len(parts) == 3 and parts[2] == "segments":
                return VirtualPath(
                    kind=PathKind.SEGMENTS,
                    crawl_id=_validate_path_component(parts[1], "crawl_id"),
                    raw_path=path,
                )
            elif len(parts) == 4:
                return VirtualPath(
                    kind=PathKind.SEGMENT,
                    crawl_id=_validate_path_component(parts[1], "crawl_id"),
                    segment_id=_validate_path_component(parts[3], "segment_id"),
                    raw_path=path,
                )
            elif len(parts) == 5:
                return VirtualPath(
                    kind=PathKind.FILE_TYPE,
                    crawl_id=_validate_path_component(parts[1], "crawl_id"),
                    segment_id=_validate_path_component(parts[3], "segment_id"),
                    file_type=_validate_file_type(parts[4]),
                    raw_path=path,
                )
            elif len(parts) >= 6:
                filename = "/".join(parts[5:])
                _validate_path_component(filename, "filename")
                return VirtualPath(
                    kind=PathKind.WARC_FILE,
                    crawl_id=_validate_path_component(parts[1], "crawl_id"),
                    segment_id=_validate_path_component(parts[3], "segment_id"),
                    file_type=_validate_file_type(parts[4]),
                    filename=filename,
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
            return (
                f"/crawls/{kwargs['crawl_id']}/segments/{kwargs['segment_id']}"
                f"/{kwargs['file_type']}"
            )
        if kind == PathKind.WARC_FILE:
            return (
                f"/crawls/{kwargs['crawl_id']}/segments/{kwargs['segment_id']}"
                f"/{kwargs['file_type']}/{kwargs['filename']}"
            )
        raise ValueError(f"Cannot build path for kind: {kind}")
