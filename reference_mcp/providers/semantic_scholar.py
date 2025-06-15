"""Semantic Scholar provider implementation."""

import os
import httpx
from typing import List
from urllib.parse import quote
from dotenv import load_dotenv

from reference_mcp.providers.base import AbstractProvider
from reference_mcp.models import Reference, ProviderMeta

# Load environment variables from .env file
load_dotenv()


class SemanticScholarProvider(AbstractProvider):
    """Semantic Scholar academic search provider."""

    NAME = "semantic_scholar"
    MAX_PER_QUERY = 100
    TIMEOUT = 4.0

    def __init__(self):
        super().__init__()
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        # Support both environment variable names
        self.api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

    async def search(self, query: str, limit: int) -> List[Reference]:
        """Search Semantic Scholar for papers."""
        fields = "title,authors,year,venue,externalIds,url,abstract,citationCount,publicationDate"
        url = (
            f"{self.base_url}/paper/search?query={quote(query)}&limit={min(limit, self.MAX_PER_QUERY)}&fields={fields}"
        )

        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.get(url, headers=headers)

            # Handle rate limiting
            if response.status_code == 429:
                return []

            response.raise_for_status()
            data = response.json()

        results = []

        for paper in data.get("data", []):
            # Extract authors
            authors = []
            for author in paper.get("authors", []):
                if author.get("name"):
                    authors.append(author["name"])

            # Extract year
            year = paper.get("year")
            if not year and paper.get("publicationDate"):
                try:
                    year = int(paper["publicationDate"][:4])
                except (ValueError, TypeError):
                    pass

            # Extract identifiers
            external_ids = paper.get("externalIds", {})
            doi = external_ids.get("DOI")
            arxiv_id = external_ids.get("ArXiv")

            # Build BibTeX
            bibtex_type = "article"
            bibtex_key = paper.get("paperId", "unknown")

            bibtex_lines = [f"@{bibtex_type}{{{bibtex_key},"]
            bibtex_lines.append(f"  title = {{{paper.get('title', '')}}}")
            bibtex_lines.append(f"  author = {{{' and '.join(authors)}}}")
            if year:
                bibtex_lines.append(f"  year = {{{year}}}")
            if paper.get("venue"):
                bibtex_lines.append(f"  journal = {{{paper.get('venue')}}}")
            if doi:
                bibtex_lines.append(f"  doi = {{{doi}}}")
            if arxiv_id:
                bibtex_lines.append(f"  eprint = {{{arxiv_id}}}")
                bibtex_lines.append("  archivePrefix = {arXiv}")
            bibtex_lines.append("}")

            bibtex = ",\n".join(bibtex_lines)

            # Create reference
            ref = Reference(
                title=paper.get("title", ""),
                authors=authors,
                year=year,
                doi=doi,
                arxiv_id=arxiv_id,
                s2_paper_id=paper.get("paperId"),
                venue=paper.get("venue"),
                bibtex=bibtex,
                citation_count=paper.get("citationCount"),
                sources=[ProviderMeta(name=self.NAME, url=paper.get("url"), raw_data=paper)],
            )

            results.append(ref)

        return results
