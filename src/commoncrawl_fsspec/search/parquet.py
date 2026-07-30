"""Parquet/DuckDB search backend."""

from __future__ import annotations

import logging
from typing import List, Optional

from ..constants import DATA_BASE_URL
from ..models import SearchRecord
from .base import SearchBackend, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class ParquetSearchBackend(SearchBackend):
    """Search backend using DuckDB and Parquet index files."""

    def __init__(self):
        self._duckdb = None

    @property
    def duckdb(self):
        """Lazy import of duckdb."""
        if self._duckdb is None:
            try:
                import duckdb
            except ImportError:
                raise ImportError(
                    "duckdb is required for parquet search backend. "
                    "Install with: pip install commoncrawl-fsspec[duckdb]"
                )
            self._duckdb = duckdb
        return self._duckdb

    def _build_parquet_url(self, crawl_id: str) -> str:
        """Build the parquet URL for a crawl."""
        return f"{DATA_BASE_URL}/cc-index/table/cc-main/warc/crawl={crawl_id}/subset=warc/*.parquet"

    def search(self, query: SearchQuery) -> SearchResult:
        """Search for records using DuckDB and Parquet."""
        parquet_url = self._build_parquet_url(query.crawl_id)

        sql = """
            SELECT urlkey, timestamp, url, mime, status, digest,
                   CAST(length AS INTEGER) as length,
                   CAST(offset AS INTEGER) as offset,
                   filename
            FROM read_parquet(?)
            WHERE url LIKE ?
            LIMIT ? OFFSET ?
        """

        conn = None
        try:
            conn = self.duckdb.connect()
            rows = conn.execute(
                sql,
                [parquet_url, query.url_pattern, query.limit, query.offset],
            ).fetchall()

            records = []
            for row in rows:
                records.append(
                    SearchRecord(
                        urlkey=row[0],
                        timestamp=row[1],
                        url=row[2],
                        mime=row[3],
                        status=row[4],
                        digest=row[5],
                        length=row[6],
                        offset=row[7],
                        filename=row[8],
                    )
                )

            return SearchResult(records=records, total=len(records))
        finally:
            if conn is not None:
                conn.close()

    def count(self, query: SearchQuery) -> int:
        """Count records using DuckDB and Parquet."""
        parquet_url = self._build_parquet_url(query.crawl_id)

        sql = """
            SELECT COUNT(*)
            FROM read_parquet(?)
            WHERE url LIKE ?
        """

        conn = None
        try:
            conn = self.duckdb.connect()
            result = conn.execute(sql, [parquet_url, query.url_pattern]).fetchone()
            return result[0] if result else 0
        finally:
            if conn is not None:
                conn.close()
