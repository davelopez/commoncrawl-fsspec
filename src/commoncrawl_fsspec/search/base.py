"""Search backend abstract base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional

from ..models import SearchRecord


@dataclass(frozen=True)
class SearchQuery:
    """Parameters for a search query."""

    crawl_id: str
    url_pattern: str
    match_type: Optional[str] = None
    limit: int = 100
    offset: int = 0
    filters: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class SearchResult:
    """Result of a search query."""

    records: List[SearchRecord]
    total: int


class SearchBackend(ABC):
    """Abstract base class for search backends."""

    @abstractmethod
    def search(self, query: SearchQuery) -> SearchResult:
        """Search for records matching the query."""
        ...

    @abstractmethod
    def count(self, query: SearchQuery) -> int:
        """Count records matching the query."""
        ...
