"""Security tests for path traversal, SSRF prevention, and cache bounds."""

import pytest
import responses
from commoncrawl_fsspec.clients.http_client import HttpClient
from commoncrawl_fsspec.constants import COLLINFO_URL, DATA_BASE_URL
from commoncrawl_fsspec.filesystem import CommonCrawlFileSystem
from commoncrawl_fsspec.paths import PathResolver


class TestPathTraversalValidation:
    """Test that path traversal attempts are rejected."""

    @pytest.mark.parametrize(
        "path",
        [
            "/crawls/../etc/passwd",
            "/crawls/../../etc/passwd",
            "/crawls/CC-MAIN-2024-33/segments/../segments/00001",
            "/crawls/CC-MAIN-2024-33/segments/00001/warc/../file.warc.gz",
        ],
    )
    def test_traversal_in_crawl_id_rejected(self, path):
        with pytest.raises(ValueError):
            PathResolver.parse(path)

    def test_double_slash_rejected(self):
        with pytest.raises(ValueError):
            PathResolver.parse("/crawls//CC-MAIN-2024-33")

    def test_invalid_file_type_rejected(self):
        with pytest.raises(ValueError):
            PathResolver.parse("/crawls/CC-MAIN-2024-33/segments/00001/invalid")

    def test_traversal_in_file_type_rejected(self):
        with pytest.raises(ValueError):
            PathResolver.parse("/crawls/CC-MAIN-2024-33/segments/00001/..")

    def test_traversal_in_filename_rejected(self):
        with pytest.raises(ValueError):
            PathResolver.parse(
                "/crawls/CC-MAIN-2024-33/segments/00001/warc/../../etc/passwd"
            )

    def test_valid_paths_still_work(self):
        vp = PathResolver.parse("/crawls/CC-MAIN-2024-33")
        assert vp.crawl_id == "CC-MAIN-2024-33"

        vp = PathResolver.parse("/crawls/CC-MAIN-2024-33/segments/00001/warc/file.gz")
        assert vp.filename == "file.gz"


class TestUrlAllowlist:
    """Test that the HTTP client rejects non-allowlisted URLs."""

    def setup_method(self):
        self.client = HttpClient()

    def test_http_scheme_rejected(self):
        with pytest.raises(ValueError, match="non-HTTPS"):
            self.client.get_json("http://data.commoncrawl.org/collinfo.json")

    def test_unknown_host_rejected(self):
        with pytest.raises(ValueError, match="not in allowlist"):
            self.client.get_json("https://evil.example.com/data")

    def test_localhost_rejected(self):
        with pytest.raises(ValueError, match="not in allowlist"):
            self.client.get_bytes("https://127.0.0.1:8080/secret")

    @responses.activate
    def test_allowed_host_accepted(self):
        responses.add(responses.GET, COLLINFO_URL, json=[], status=200)
        result = self.client.get_json(COLLINFO_URL)
        assert result == []


class TestBoundedManifestCache:
    """Test that the manifest cache evicts old entries."""

    @responses.activate
    def test_cache_eviction(self):
        from commoncrawl_fsspec.clients.s3_listing_client import (
            MAX_MANIFEST_CACHE_ENTRIES,
            S3ListingClient,
        )

        import gzip

        client = S3ListingClient()

        for i in range(MAX_MANIFEST_CACHE_ENTRIES + 2):
            crawl_id = f"CC-MAIN-2024-{i:02d}"
            manifest_url = f"{DATA_BASE_URL}/crawl-data/{crawl_id}/warc.paths.gz"
            body = gzip.compress(
                f"crawl-data/{crawl_id}/segments/seg{i}/warc/file{i}.warc.gz".encode()
            )
            responses.add(responses.GET, manifest_url, body=body, status=200)
            client._load_manifest(crawl_id, "warc")

        assert len(client._manifest_cache) == MAX_MANIFEST_CACHE_ENTRIES
        first_key = ("CC-MAIN-2024-00", "warc")
        assert first_key not in client._manifest_cache
        last_key = (
            f"CC-MAIN-2024-{MAX_MANIFEST_CACHE_ENTRIES + 1:02d}",
            "warc",
        )
        assert last_key in client._manifest_cache


class TestFilesystemSecurityIntegration:
    """Test that the filesystem rejects traversal paths."""

    @responses.activate
    def test_traversal_path_rejected_by_ls(self):
        responses.add(responses.GET, COLLINFO_URL, json=[], status=200)
        fs = CommonCrawlFileSystem()
        with pytest.raises(ValueError):
            fs.ls("/crawls/../etc/passwd")

    @responses.activate
    def test_traversal_path_rejected_by_info(self):
        responses.add(responses.GET, COLLINFO_URL, json=[], status=200)
        fs = CommonCrawlFileSystem()
        with pytest.raises(ValueError):
            fs.info("/crawls/../../etc/passwd")
