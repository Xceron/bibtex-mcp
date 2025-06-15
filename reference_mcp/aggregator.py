"""Aggregator for deduplicating and ranking search results."""

import asyncio
from typing import List, Optional, Set, Tuple
from rapidfuzz import fuzz

from reference_mcp.models import Reference
from reference_mcp.providers.base import AbstractProvider


async def fanout(
    query: str, k: int, providers: List[AbstractProvider], year: Optional[int] = None, author: Optional[str] = None
) -> List[Reference]:
    """Execute search across all providers concurrently with timeout handling."""

    async def search_with_timeout(provider: AbstractProvider) -> List[Reference]:
        try:
            return await asyncio.wait_for(provider.cached_search(query, k, year, author), timeout=provider.TIMEOUT)
        except asyncio.TimeoutError:
            return []
        except Exception:
            # Provider failed, return empty list
            return []

    # Use TaskGroup for concurrent execution (Python 3.11+)
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(search_with_timeout(p)) for p in providers]

    # Flatten results
    results = []
    for task in tasks:
        results.extend(task.result())

    return results


def _normalize_doi(doi: Optional[str]) -> Optional[str]:
    """Normalize DOI for comparison."""
    if not doi:
        return None
    # Remove common prefixes and convert to lowercase
    doi = doi.lower().strip()
    if doi.startswith("https://doi.org/"):
        doi = doi[16:]
    elif doi.startswith("http://doi.org/"):
        doi = doi[15:]
    elif doi.startswith("doi:"):
        doi = doi[4:]
    return doi


def _normalize_arxiv_id(arxiv_id: Optional[str]) -> Optional[str]:
    """Normalize arXiv ID for comparison."""
    if not arxiv_id:
        return None
    # Remove version suffix and normalize format
    arxiv_id = arxiv_id.strip()
    if "v" in arxiv_id:
        arxiv_id = arxiv_id.split("v")[0]
    return arxiv_id


def _extract_first_author_lastname(authors: List[str]) -> str:
    """Extract first author's last name for comparison."""
    if not authors:
        return ""
    first_author = authors[0]
    # Simple heuristic: last word is usually last name
    parts = first_author.strip().split()
    return parts[-1].lower() if parts else ""


def _are_duplicates(ref1: Reference, ref2: Reference) -> bool:
    """Determine if two references are duplicates."""
    # Fast path: check hard identifiers
    if ref1.doi and ref2.doi:
        if _normalize_doi(ref1.doi) == _normalize_doi(ref2.doi):
            return True

    if ref1.arxiv_id and ref2.arxiv_id:
        if _normalize_arxiv_id(ref1.arxiv_id) == _normalize_arxiv_id(ref2.arxiv_id):
            return True

    if ref1.s2_paper_id and ref2.s2_paper_id:
        if ref1.s2_paper_id == ref2.s2_paper_id:
            return True

    # Fuzzy fallback: title + first author + year
    title_similarity = fuzz.token_set_ratio(ref1.title.lower(), ref2.title.lower())

    if title_similarity >= 94:
        # Check year match
        if ref1.year and ref2.year and ref1.year != ref2.year:
            return False

        # Check first author similarity
        author1 = _extract_first_author_lastname(ref1.authors)
        author2 = _extract_first_author_lastname(ref2.authors)

        if author1 and author2:
            author_similarity = fuzz.ratio(author1, author2)
            return author_similarity >= 80

        # If we can't compare authors but titles are very similar, consider them duplicates
        return title_similarity >= 98

    return False


def dedupe_rank(references: List[Reference], max_results: int) -> List[Reference]:
    """Deduplicate and rank references."""
    if not references:
        return []

    # Group duplicates
    merged_refs: List[Reference] = []
    processed_indices: Set[int] = set()

    for i, ref in enumerate(references):
        if i in processed_indices:
            continue

        # Find all duplicates of this reference
        current_ref = ref.model_copy(deep=True)
        processed_indices.add(i)

        for j in range(i + 1, len(references)):
            if j in processed_indices:
                continue

            if _are_duplicates(current_ref, references[j]):
                # Merge the duplicate into current_ref
                current_ref.merge_with(references[j])
                processed_indices.add(j)

        merged_refs.append(current_ref)

    # Sort by score (primary), then by year (secondary)
    def sort_key(ref: Reference) -> Tuple:
        return (
            -ref.score,  # Higher score first
            -(ref.year or 0),  # More recent first
            ref.title.lower(),  # Alphabetical as final tiebreaker
        )

    merged_refs.sort(key=sort_key)

    # Return top k results
    return merged_refs[:max_results]
