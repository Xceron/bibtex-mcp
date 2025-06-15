"""Base provider class for academic search providers."""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timedelta

from ..models import Reference


class AbstractProvider(ABC):
    """Abstract base class for academic search providers."""

    NAME: str = ""
    MAX_PER_QUERY: int = 20
    TIMEOUT: float = 4.0

    def __init__(self):
        self._cache: dict = {}
        self._cache_expiry: dict = {}

    @abstractmethod
    async def search(
        self, query: str, limit: int, year: Optional[int] = None, author: Optional[str] = None
    ) -> List[Reference]:
        """Search the provider for references matching the query.

        Args:
            query: Free-text search string
            limit: Maximum number of results to return
            year: Optional year filter (papers published in or after this year)
            author: Optional author name filter

        Returns:
            List of Reference objects
        """
        pass

    def _cache_key(self, query: str, limit: int, year: Optional[int] = None, author: Optional[str] = None) -> str:
        """Generate cache key for query."""
        return f"{self.NAME}:{query}:{limit}:{year}:{author}"

    async def cached_search(
        self, query: str, limit: int, year: Optional[int] = None, author: Optional[str] = None
    ) -> List[Reference]:
        """Search with simple LRU caching (15 minutes)."""
        cache_key = self._cache_key(query, limit, year, author)
        now = datetime.now()

        # Check cache
        if cache_key in self._cache:
            if self._cache_expiry[cache_key] > now:
                return self._cache[cache_key]
            else:
                # Expired, remove from cache
                del self._cache[cache_key]
                del self._cache_expiry[cache_key]

        # Fetch fresh results
        results = await self.search(query, min(limit, self.MAX_PER_QUERY), year, author)

        # Cache results
        self._cache[cache_key] = results
        self._cache_expiry[cache_key] = now + timedelta(minutes=15)

        # Simple LRU: if cache too large, remove oldest entries
        if len(self._cache) > 100:
            oldest_key = min(self._cache_expiry.keys(), key=lambda k: self._cache_expiry[k])
            del self._cache[oldest_key]
            del self._cache_expiry[oldest_key]

        return results
