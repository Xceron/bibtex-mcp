import json
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from threading import Lock
import hashlib

from fastmcp import FastMCP

from reference_mcp.aggregator import fanout, dedupe_rank
from reference_mcp.models import SearchInput
from reference_mcp.providers.registry import get_providers

logger = logging.getLogger(__name__)
mcp = FastMCP("ReferenceSearch")


@dataclass
class CacheEntry:
    """Cache entry with expiration time."""

    data: Any
    expires_at: datetime


class SimpleCache:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, ttl_minutes: int = 10):
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl = timedelta(minutes=ttl_minutes)
        self._lock = Lock()
        # Secondary index for ID to cache keys mapping
        self._id_to_keys: Dict[str, set] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        with self._lock:
            # Clean expired entries periodically
            self._clean_expired_if_needed()

            if key in self._cache:
                entry = self._cache[key]
                if datetime.now() < entry.expires_at:
                    return entry.data
                else:
                    # Clean up expired entry
                    self._remove_entry(key)
            return None

    def set(self, key: str, value: Any) -> None:
        """Set value in cache with TTL."""
        expires_at = datetime.now() + self._ttl
        with self._lock:
            self._cache[key] = CacheEntry(data=value, expires_at=expires_at)

            # Update ID index for search results
            if key.startswith("search:") and isinstance(value, list):
                for ref in value:
                    ref_id = self._get_ref_id(ref)
                    if ref_id not in self._id_to_keys:
                        self._id_to_keys[ref_id] = set()
                    self._id_to_keys[ref_id].add(key)

    def get_by_id(self, doc_id: str) -> Optional[Tuple[str, Dict]]:
        """Get reference by ID from any cached search result."""
        with self._lock:
            if doc_id in self._id_to_keys:
                for cache_key in self._id_to_keys[doc_id]:
                    if cache_key in self._cache:
                        entry = self._cache[cache_key]
                        if datetime.now() < entry.expires_at:
                            # Find the specific reference
                            for ref in entry.data:
                                if self._get_ref_id(ref) == doc_id:
                                    return cache_key, ref
                        else:
                            self._remove_entry(cache_key)
            return None

    def clear_expired(self) -> None:
        """Remove all expired entries."""
        with self._lock:
            now = datetime.now()
            expired_keys = [k for k, v in self._cache.items() if v.expires_at <= now]
            for key in expired_keys:
                self._remove_entry(key)

    def _clean_expired_if_needed(self) -> None:
        """Clean expired entries periodically (every 100 accesses)."""
        # Simple heuristic: clean every 100 cache accesses
        if len(self._cache) > 100 and len(self._cache) % 100 == 0:
            self.clear_expired()

    def _remove_entry(self, key: str) -> None:
        """Remove entry and update indices."""
        if key in self._cache:
            # Update ID index
            if key.startswith("search:") and isinstance(self._cache[key].data, list):
                for ref in self._cache[key].data:
                    ref_id = self._get_ref_id(ref)
                    if ref_id in self._id_to_keys:
                        self._id_to_keys[ref_id].discard(key)
                        if not self._id_to_keys[ref_id]:
                            del self._id_to_keys[ref_id]
            del self._cache[key]

    @staticmethod
    def _get_ref_id(ref: Dict) -> str:
        """Get stable ID for a reference."""
        # Use existing identifiers or create hash from title
        base_id = ref.get("doi") or ref.get("arxiv_id") or ref.get("s2_paper_id") or ref.get("dblp_key")
        if base_id:
            return base_id
        # For title-based IDs, use hash to avoid collisions
        title = ref.get("title", "")
        return f"title_hash_{hashlib.md5(title.encode()).hexdigest()[:16]}"


# Global cache instance
search_cache = SimpleCache(ttl_minutes=10)


@mcp.tool(name="search_reference")
async def search_reference(
    query: str, max_results: int = 20, year: Optional[int] = None, author: Optional[str] = None
) -> str:
    """
    Search academic literature databases (DBLP, Semantic Scholar, arXiv, OpenAlex) to find research papers and return properly formatted BibTeX citations.

    Use this tool when the user needs:
    - Academic citations for research papers, articles, or publications
    - BibTeX entries for bibliography management
    - Information about specific papers (authors, venue, publication year, abstract)
    - Literature search results from computer science and AI databases

    The tool automatically searches all major academic databases, deduplicates results, and ranks by relevance.
    Each result includes complete bibliographic metadata and a ready-to-use BibTeX citation.

    Args:
        query: Academic search terms (paper titles, author names, years or any combination of them yields the best results).
        max_results: Number of results to return (1-100, default 20). Use lower values (5-10) for focused searches.
        year: Optional year filter. If provided, returns papers published in this year.
        author: Optional author name filter. If provided, returns papers by authors matching this name.

    Returns:
        Dictionary with query, total_results count, and array of references containing:
        - Complete bibliographic data (title, authors, year, venue, DOI, etc.)
        - Abstract text when available
        - Formatted BibTeX citation ready for use
        - Citation count
        - Source databases that found this reference
    """
    logger.info(f"Tool called with query: {query}, max_results: {max_results}, year: {year}, author: {author}")

    try:
        # Validate input
        input_data = SearchInput(
            query=query,
            max_results=max_results,
            providers=None,  # Always use all providers
        )

        # Get all provider instances
        provider_instances = get_providers(None)
        logger.info(f"Using all providers: {[p.NAME for p in provider_instances]}")

        # Execute parallel search with filters - over-fetch for better deduplication
        all_results = await fanout(
            input_data.query,
            input_data.max_results * 2,  # Over-fetch for better deduplication
            provider_instances,
            year=year,
            author=author,
        )
        logger.info(f"Raw results count: {len(all_results)}")

        # Deduplicate and rank results
        final_results = dedupe_rank(all_results, input_data.max_results)
        logger.info(f"Final results count: {len(final_results)}")

        # Format response as JSON string for display
        result = {
            "references": [ref.model_dump() for ref in final_results],
            "total_found": len(final_results),
            "query": query,
        }
        if year:
            result["year_filter"] = year
        if author:
            result["author_filter"] = author
        logger.info(f"Returning result with {len(final_results)} references")
        return json.dumps(result, indent=2, ensure_ascii=False)

    except Exception as e:
        logger.error(f"Error in search_reference: {e}")
        raise


@mcp.tool(name="search")
async def search(query: str, top_k: int = 10) -> list[dict]:
    """
    Search academic literature and return lightweight results for browsing.

    This is the recall step - returns compact metadata to help decide which documents to fetch.
    Each result contains only essential information: ID, title, and a snippet.

    Args:
        query: Search terms (paper titles, author names, keywords)
        top_k: Number of results to return (default 10)

    Returns:
        List of lightweight result objects with id, title, and snippet fields
    """
    logger.info(f"Search tool called with query: {query}, top_k: {top_k}")

    # Input validation
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")
    if top_k < 1 or top_k > 100:
        raise ValueError("top_k must be between 1 and 100")

    try:
        # Check cache first - use hash for better collision resistance
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        cache_key = f"search:{query_hash}:{top_k}"
        cached_full_results = search_cache.get(cache_key)

        if cached_full_results is None:
            # Call the existing search_reference function
            raw_json = await search_reference(query=query, max_results=top_k)
            data = json.loads(raw_json)
            # Cache the full results for fetch to use
            search_cache.set(cache_key, data["references"])
            cached_full_results = data["references"]

        # Build lightweight results
        hits = []
        for ref in cached_full_results:
            # Use consistent ID generation with cache
            ref_id = SimpleCache._get_ref_id(ref)

            # Create snippet from abstract or venue info
            snippet = ""
            if ref.get("abstract"):
                snippet = ref["abstract"][:200] + "..." if len(ref["abstract"]) > 200 else ref["abstract"]
            elif ref.get("venue"):
                snippet = f"Published in {ref['venue']}"
                if ref.get("year"):
                    snippet += f" ({ref['year']})"

            hits.append({"id": ref_id, "title": ref["title"], "snippet": snippet})

        logger.info(f"Returning {len(hits)} lightweight results")
        return hits

    except Exception as e:
        logger.error(f"Error in search tool: {e}")
        raise


@mcp.tool(name="fetch")
async def fetch(ids: list[str]) -> dict[str, str]:
    """
    Fetch full documents for previously searched references.

    This is the precision step - returns complete BibTeX records and abstracts
    for documents identified by the search tool.

    Args:
        ids: List of document IDs from previous search results

    Returns:
        Dictionary mapping IDs to full document text (BibTeX + abstract)
    """
    logger.info(f"Fetch tool called with {len(ids)} IDs")

    # Input validation
    if not ids:
        return {}
    if len(ids) > 50:
        raise ValueError("Cannot fetch more than 50 documents at once")

    results: dict[str, str] = {}

    for doc_id in ids:
        try:
            # Use optimized cache lookup
            cache_result = search_cache.get_by_id(doc_id)

            if cache_result:
                _, ref = cache_result
                # Format the full document
                bibtex = ref["bibtex"]
                abstract = ref.get("abstract", "")

                if abstract:
                    results[doc_id] = f"{bibtex}\n\nAbstract:\n{abstract}"
                else:
                    results[doc_id] = bibtex
            else:
                # If not found in cache, search for it specifically
                logger.info(f"ID {doc_id} not found in cache, searching...")
                try:
                    raw_json = await search_reference(query=doc_id, max_results=1)
                    data = json.loads(raw_json)

                    if data["references"]:
                        ref = data["references"][0]
                        # Check if this ref matches the requested ID
                        found_ref_id = SimpleCache._get_ref_id(ref)

                        if found_ref_id == doc_id:
                            bibtex = ref["bibtex"]
                            abstract = ref.get("abstract", "")

                            if abstract:
                                results[doc_id] = f"{bibtex}\n\nAbstract:\n{abstract}"
                            else:
                                results[doc_id] = bibtex
                        else:
                            logger.warning(f"Found reference doesn't match requested ID: {doc_id}")
                    else:
                        logger.warning(f"No results found for ID: {doc_id}")

                except Exception as search_error:
                    logger.error(f"Error searching for ID {doc_id}: {search_error}")
                    # Continue with other IDs instead of failing entire operation

        except Exception as e:
            logger.error(f"Error processing ID {doc_id}: {e}")
            # Continue with other IDs

    logger.info(f"Returning {len(results)} full documents out of {len(ids)} requested")
    return results
