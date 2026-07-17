"""Factory for creating search backends."""

from __future__ import annotations

from typing import Optional

from ..clients.http_client import HttpClient
from .base import SearchBackend
from .cdx import CdxSearchBackend
from .parquet import ParquetSearchBackend


def create_search_backend(
    backend_name: str,
    http_client: Optional[HttpClient] = None,
    cdx_api_map: Optional[dict] = None,
) -> SearchBackend:
    """Create a search backend based on the name.

    Args:
        backend_name: "cdx" or "parquet"
        http_client: HTTP client (required for CDX backend)
        cdx_api_map: Optional map of crawl_id to CDX API URL

    Returns:
        SearchBackend instance

    Raises:
        ValueError: If backend_name is not recognized
        ImportError: If required dependencies are missing
    """
    if backend_name == "cdx":
        if http_client is None:
            raise ValueError("http_client is required for CDX backend")
        return CdxSearchBackend(http_client, cdx_api_map)
    elif backend_name == "parquet":
        return ParquetSearchBackend()
    else:
        raise ValueError(
            f"Unknown search backend: {backend_name}. Must be 'cdx' or 'parquet'."
        )
