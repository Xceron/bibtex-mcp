import logging
from fastmcp import FastMCP
from typing import Dict, Any, Optional
import json
from reference_mcp.models import SearchInput
from reference_mcp.providers.registry import get_providers
from reference_mcp.aggregator import fanout, dedupe_rank

logger = logging.getLogger(__name__)
mcp = FastMCP("ReferenceSearch")


@mcp.tool(name="search_reference")
async def search_reference(
    query: str, max_results: int = 20, year: Optional[int] = None, author: Optional[str] = None
) -> Dict[str, Any]:
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
        query: Academic search terms (paper titles, author names, keywords, concepts).
               Examples: "transformer architecture", "John Smith machine learning", "BERT language model"
        max_results: Number of results to return (1-100, default 20). Use lower values (5-10) for focused searches.
        year: Optional year filter. If provided, returns papers published in or after this year.
        author: Optional author name filter. If provided, returns papers by authors matching this name.

    Returns:
        Dictionary with query, total_results count, and array of references containing:
        - Complete bibliographic data (title, authors, year, venue, DOI, etc.)
        - Abstract text when available
        - Formatted BibTeX citation ready for use
        - Citation count and relevance score
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

        # Execute parallel search with filters - overfetch for better deduplication
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
