"""arXiv provider implementation."""

import httpx
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import quote
import re

from reference_mcp.providers.base import AbstractProvider
from reference_mcp.models import Reference, ProviderMeta


class ArxivProvider(AbstractProvider):
    """arXiv preprint repository provider."""

    NAME = "arxiv"
    MAX_PER_QUERY = 50
    TIMEOUT = 5.0  # arXiv can be slower

    def __init__(self):
        super().__init__()
        self.base_url = "http://export.arxiv.org/api/query"

    async def search(
        self, query: str, limit: int, year: Optional[int] = None, author: Optional[str] = None
    ) -> List[Reference]:
        """Search arXiv for papers."""
        # Build search query with filters
        search_parts = [f"all:{quote(query)}"]

        # Add author filter using au: prefix
        if author:
            search_parts.append(f"au:{quote(author)}")

        # Join with AND operator
        search_query = "+AND+".join(search_parts)

        # Add date filter if year is provided (submittedDate:[YYYY0101 TO *])
        if year:
            search_query += f"+AND+submittedDate:[{year}0101+TO+*]"

        url = f"{self.base_url}?search_query={search_query}&start=0&max_results={min(limit, self.MAX_PER_QUERY)}"

        headers = {"User-Agent": "BibTeX-MCP/1.0 (https://github.com/Xceron/bibtex-mcp)"}

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            content = response.text

        # Parse XML
        root = ET.fromstring(content)

        # Define namespaces
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        results = []

        for entry in root.findall("atom:entry", ns):
            # Extract title and clean it
            title_elem = entry.find("atom:title", ns)
            title = title_elem.text if title_elem is not None else ""
            title = re.sub(r"\s+", " ", title).strip()

            # Extract authors
            authors = []
            for author in entry.findall("atom:author", ns):
                name_elem = author.find("atom:name", ns)
                if name_elem is not None and name_elem.text:
                    authors.append(name_elem.text.strip())

            # Extract arxiv ID from id URL
            id_elem = entry.find("atom:id", ns)
            arxiv_id = ""
            if id_elem is not None and id_elem.text:
                match = re.search(r"arxiv\.org/abs/(.+)$", id_elem.text)
                if match:
                    arxiv_id = match.group(1)

            # Extract year from published date
            year = None
            published_elem = entry.find("atom:published", ns)
            if published_elem is not None and published_elem.text:
                try:
                    year = int(published_elem.text[:4])
                except (ValueError, TypeError):
                    pass

            # Extract categories
            categories = []
            for cat in entry.findall("atom:category", ns):
                term = cat.get("term")
                if term:
                    categories.append(term)

            # Build BibTeX
            bibtex_key = arxiv_id.replace("/", "_") if arxiv_id else "unknown"

            bibtex_lines = [
                f"@article{{{bibtex_key},",
                f"  title = {{{title}}}",
                f"  author = {{{' and '.join(authors)}}}",
            ]
            if year:
                bibtex_lines.append(f"  year = {{{year}}}")
            bibtex_lines.append(f"  eprint = {{{arxiv_id}}}")
            bibtex_lines.append("  archivePrefix = {arXiv}")
            if categories:
                bibtex_lines.append(f"  primaryClass = {{{categories[0]}}}")
            bibtex_lines.append("}")

            bibtex = ",\n".join(bibtex_lines)

            # Get URL
            url = f"https://arxiv.org/abs/{arxiv_id}"

            # Create reference
            ref = Reference(
                title=title,
                authors=authors,
                year=year,
                arxiv_id=arxiv_id,
                bibtex=bibtex,
                sources=[
                    ProviderMeta(
                        name=self.NAME,
                        url=url,
                        raw_data={
                            "categories": categories,
                            "published": published_elem.text if published_elem is not None else None,
                        },
                    )
                ],
            )

            results.append(ref)

        return results
