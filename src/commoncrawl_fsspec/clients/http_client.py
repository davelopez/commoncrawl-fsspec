"""HTTP client for Common Crawl APIs."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..constants import DEFAULT_REQUEST_TIMEOUT, DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

ALLOWED_HOSTS = frozenset(
    {
        "data.commoncrawl.org",
        "index.commoncrawl.org",
    }
)


def _validate_url(url: str) -> str:
    """Validate that a URL uses HTTPS and points to an allowed host."""
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise ValueError(f"Refusing non-HTTPS URL: {url}")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"URL host not in allowlist: {parsed.hostname}")
    return url


class HttpClient:
    """HTTP client with retry and User-Agent configuration."""

    def __init__(
        self,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: int = DEFAULT_REQUEST_TIMEOUT,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})
        self.timeout = timeout

        retry = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """GET request returning parsed JSON."""
        _validate_url(url)
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_text(self, url: str, params: Optional[Dict[str, Any]] = None) -> str:
        """GET request returning text."""
        _validate_url(url)
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.text

    def get_bytes(self, url: str, params: Optional[Dict[str, Any]] = None) -> bytes:
        """GET request returning raw bytes."""
        _validate_url(url)
        resp = self.session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.content

    def head(self, url: str, params: Optional[Dict[str, Any]] = None):
        """HEAD request returning the response object."""
        _validate_url(url)
        resp = self.session.head(
            url,
            params=params,
            timeout=self.timeout,
            allow_redirects=True,
        )
        resp.raise_for_status()
        return resp

    def get_range(self, url: str, start: int, end: int) -> bytes:
        """GET request with byte range header."""
        _validate_url(url)
        headers = {"Range": f"bytes={start}-{end - 1}"}
        resp = self.session.get(url, headers=headers, timeout=self.timeout, stream=True)
        resp.raise_for_status()
        return resp.content

    def close(self):
        """Close the underlying session."""
        self.session.close()
