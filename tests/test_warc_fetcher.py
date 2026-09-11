"""Tests for WARC record fetcher."""

import responses
from commoncrawl_fsspec.clients.http_client import HttpClient
from commoncrawl_fsspec.clients.warc_fetcher import WarcRecordFetcher
from commoncrawl_fsspec.constants import DATA_BASE_URL


class TestWarcRecordFetcher:
    """Test WarcRecordFetcher."""

    @responses.activate
    def test_fetch_record(self):
        """Test fetching a WARC record with byte range."""
        filename = "CC-MAIN-2024.warc.gz"
        url = f"{DATA_BASE_URL}/{filename}"
        mock_data = b"\x1f\x8b\x08\x00" + b"\x00" * 100  # gzip header + padding
        offset = 5000
        length = 100

        responses.add(
            responses.GET,
            url,
            body=mock_data,
            status=206,
            adding_headers={
                "Content-Range": f"bytes {offset}-{offset + length - 1}/{len(mock_data)}"
            },
        )

        http_client = HttpClient()
        fetcher = WarcRecordFetcher(http_client)
        data = fetcher.fetch_record(filename, offset, length)

        assert data == mock_data

    @responses.activate
    def test_fetch_record_stream(self):
        """Test fetching a WARC record as a stream."""
        filename = "CC-MAIN-2024.warc.gz"
        url = f"{DATA_BASE_URL}/{filename}"
        mock_data = b"\x1f\x8b\x08\x00" + b"\x00" * 100
        offset = 5000
        length = 100

        responses.add(
            responses.GET,
            url,
            body=mock_data,
            status=206,
        )

        http_client = HttpClient()
        fetcher = WarcRecordFetcher(http_client)
        stream = fetcher.fetch_record_stream(filename, offset, length)

        assert stream.read() == mock_data
