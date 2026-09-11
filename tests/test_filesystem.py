"""Tests for filesystem orchestrator."""

import gzip

import pytest
import responses
from commoncrawl_fsspec.filesystem import CommonCrawlFileSystem
from commoncrawl_fsspec.constants import COLLINFO_URL


class TestCommonCrawlFileSystem:
    """Test CommonCrawlFileSystem."""

    @responses.activate
    def test_ls_segments_from_manifest(self):
        """Test listing segments from a crawl manifest."""
        crawl_id = "CC-MAIN-2026-25"
        manifest_url = (
            f"https://data.commoncrawl.org/crawl-data/{crawl_id}/warc.paths.gz"
        )
        manifest_lines = "\n".join(
            [
                f"crawl-data/{crawl_id}/segments/1780687572080.85/warc/file-00000.warc.gz",
                f"crawl-data/{crawl_id}/segments/1780687572080.85/warc/file-00001.warc.gz",
                f"crawl-data/{crawl_id}/segments/1780687572081.86/warc/file-00000.warc.gz",
            ]
        )
        responses.add(
            responses.GET,
            manifest_url,
            body=gzip.compress(manifest_lines.encode("utf-8")),
            status=200,
        )

        fs = CommonCrawlFileSystem()
        entries = fs.ls(f"/crawls/{crawl_id}/segments")

        assert [entry["name"] for entry in entries] == [
            f"/crawls/{crawl_id}/segments/1780687572080.85",
            f"/crawls/{crawl_id}/segments/1780687572081.86",
        ]

    @responses.activate
    def test_ls_files_from_manifest(self):
        """Test listing files within a file type directory."""
        crawl_id = "CC-MAIN-2026-24"
        segment_id = "1780687572080.85"
        file_type = "warc"
        manifest_url = (
            f"https://data.commoncrawl.org/crawl-data/{crawl_id}/{file_type}.paths.gz"
        )
        file_path = (
            f"crawl-data/{crawl_id}/segments/{segment_id}/{file_type}/"
            "file-00000.warc.gz"
        )
        responses.add(
            responses.GET,
            manifest_url,
            body=gzip.compress(file_path.encode("utf-8")),
            status=200,
        )
        responses.add(
            responses.HEAD,
            f"https://data.commoncrawl.org/{file_path}",
            headers={
                "Content-Length": "1234",
                "Last-Modified": "Sat, 06 Jun 2026 00:52:42 GMT",
            },
            status=200,
        )

        fs = CommonCrawlFileSystem()
        entries = fs.ls(f"/crawls/{crawl_id}/segments/{segment_id}/{file_type}")

        assert len(entries) == 1
        assert entries[0]["name"] == (
            f"/crawls/{crawl_id}/segments/{segment_id}/{file_type}/file-00000.warc.gz"
        )
        assert entries[0]["size"] == 1234

    @responses.activate
    def test_ls_root(self):
        """Test listing root directory."""
        mock_data = []
        responses.add(responses.GET, COLLINFO_URL, json=mock_data, status=200)

        fs = CommonCrawlFileSystem()
        entries = fs.ls("/")

        assert len(entries) == 1
        names = [e["name"] for e in entries]
        assert "/crawls" in names

    @responses.activate
    def test_ls_crawls(self):
        """Test listing crawls directory."""
        mock_data = [
            {
                "id": "CC-MAIN-2024-33",
                "name": "CC-MAIN-2024-33",
                "cdx_api": "https://index.commoncrawl.org/CC-MAIN-2024-33-index",
                "time_from": "20240801000000",
                "time_to": "20240831235959",
            },
        ]
        responses.add(responses.GET, COLLINFO_URL, json=mock_data, status=200)

        fs = CommonCrawlFileSystem()
        entries = fs.ls("/crawls")

        assert len(entries) == 1
        assert entries[0]["name"] == "/crawls/CC-MAIN-2024-33"
        assert entries[0]["type"] == "directory"

    @responses.activate
    def test_info_root(self):
        """Test info on root."""
        mock_data = []
        responses.add(responses.GET, COLLINFO_URL, json=mock_data, status=200)

        fs = CommonCrawlFileSystem()
        info = fs.info("/")

        assert info["name"] == "/"
        assert info["type"] == "directory"

    @responses.activate
    def test_info_warc_file(self):
        """Test info on a crawl-data file path."""
        crawl_id = "CC-MAIN-2026-23"
        segment_id = "1780687572080.85"
        file_type = "warc"
        file_name = "file-00000.warc.gz"
        file_path = (
            f"crawl-data/{crawl_id}/segments/{segment_id}/{file_type}/{file_name}"
        )
        responses.add(
            responses.HEAD,
            f"https://data.commoncrawl.org/{file_path}",
            headers={
                "Content-Length": "1234",
                "Last-Modified": "Sat, 06 Jun 2026 00:52:42 GMT",
            },
            status=200,
        )

        fs = CommonCrawlFileSystem()
        info = fs.info(
            f"/crawls/{crawl_id}/segments/{segment_id}/{file_type}/{file_name}"
        )

        assert info["name"] == (
            f"/crawls/{crawl_id}/segments/{segment_id}/{file_type}/{file_name}"
        )
        assert info["type"] == "file"
        assert info["size"] == 1234

    @responses.activate
    def test_readonly_operations_raise(self):
        """Test that write operations raise NotImplementedError."""
        mock_data = []
        responses.add(responses.GET, COLLINFO_URL, json=mock_data, status=200)

        fs = CommonCrawlFileSystem()

        with pytest.raises(NotImplementedError):
            fs.rm("/test")

        with pytest.raises(NotImplementedError):
            fs.mkdir("/test")

        with pytest.raises(NotImplementedError):
            fs.rmdir("/test")

        with pytest.raises(NotImplementedError):
            fs.mv("/test1", "/test2")

        with pytest.raises(NotImplementedError):
            fs.copy("/test1", "/test2")

        with pytest.raises(NotImplementedError):
            fs.pipe_file("/test", b"data")

        with pytest.raises(NotImplementedError):
            fs.put_file("/local", "/remote")

    @responses.activate
    def test_invalidate_cache(self):
        """Test cache invalidation."""
        mock_data = []
        responses.add(responses.GET, COLLINFO_URL, json=mock_data, status=200)

        fs = CommonCrawlFileSystem()
        fs.ls("/crawls")  # populate cache
        fs.invalidate_cache()
        assert fs.crawl_list_cache.get() is None
