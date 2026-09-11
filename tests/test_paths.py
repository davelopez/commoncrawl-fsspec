"""Tests for path parsing and building."""

import pytest

from commoncrawl_fsspec.paths import PathKind, PathResolver


class TestPathResolverParse:
    """Test path parsing."""

    def test_root_path(self):
        vp = PathResolver.parse("/")
        assert vp.kind == PathKind.ROOT

    def test_empty_path(self):
        vp = PathResolver.parse("")
        assert vp.kind == PathKind.ROOT

    def test_crawls_path(self):
        vp = PathResolver.parse("/crawls")
        assert vp.kind == PathKind.CRAWLS

    def test_crawl_path(self):
        vp = PathResolver.parse("/crawls/CC-MAIN-2024-33")
        assert vp.kind == PathKind.CRAWL
        assert vp.crawl_id == "CC-MAIN-2024-33"

    def test_segments_path(self):
        vp = PathResolver.parse("/crawls/CC-MAIN-2024-33/segments")
        assert vp.kind == PathKind.SEGMENTS
        assert vp.crawl_id == "CC-MAIN-2024-33"

    def test_segment_path(self):
        vp = PathResolver.parse("/crawls/CC-MAIN-2024-33/segments/00001")
        assert vp.kind == PathKind.SEGMENT
        assert vp.crawl_id == "CC-MAIN-2024-33"
        assert vp.segment_id == "00001"

    def test_file_type_path(self):
        vp = PathResolver.parse("/crawls/CC-MAIN-2024-33/segments/00001/warc")
        assert vp.kind == PathKind.FILE_TYPE
        assert vp.crawl_id == "CC-MAIN-2024-33"
        assert vp.segment_id == "00001"
        assert vp.file_type == "warc"

    def test_warc_file_path(self):
        vp = PathResolver.parse(
            "/crawls/CC-MAIN-2024-33/segments/00001/warc/CC-MAIN-2024.warc.gz"
        )
        assert vp.kind == PathKind.WARC_FILE
        assert vp.crawl_id == "CC-MAIN-2024-33"
        assert vp.segment_id == "00001"
        assert vp.file_type == "warc"
        assert vp.filename == "CC-MAIN-2024.warc.gz"

    def test_invalid_path(self):
        with pytest.raises(ValueError):
            PathResolver.parse("/invalid/path")


class TestPathResolverBuild:
    """Test path building."""

    def test_build_root(self):
        assert PathResolver.build(PathKind.ROOT) == "/"

    def test_build_crawls(self):
        assert PathResolver.build(PathKind.CRAWLS) == "/crawls"

    def test_build_crawl(self):
        assert (
            PathResolver.build(PathKind.CRAWL, crawl_id="CC-MAIN-2024-33")
            == "/crawls/CC-MAIN-2024-33"
        )

    def test_build_segments(self):
        assert (
            PathResolver.build(PathKind.SEGMENTS, crawl_id="CC-MAIN-2024-33")
            == "/crawls/CC-MAIN-2024-33/segments"
        )

    def test_build_segment(self):
        assert (
            PathResolver.build(
                PathKind.SEGMENT, crawl_id="CC-MAIN-2024-33", segment_id="00001"
            )
            == "/crawls/CC-MAIN-2024-33/segments/00001"
        )

    def test_build_file_type(self):
        assert (
            PathResolver.build(
                PathKind.FILE_TYPE,
                crawl_id="CC-MAIN-2024-33",
                segment_id="00001",
                file_type="warc",
            )
            == "/crawls/CC-MAIN-2024-33/segments/00001/warc"
        )

    def test_build_warc_file(self):
        assert (
            PathResolver.build(
                PathKind.WARC_FILE,
                crawl_id="CC-MAIN-2024-33",
                segment_id="00001",
                file_type="warc",
                filename="CC-MAIN-2024.warc.gz",
            )
            == "/crawls/CC-MAIN-2024-33/segments/00001/warc/CC-MAIN-2024.warc.gz"
        )
