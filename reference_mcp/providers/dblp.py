"""DBLP provider implementation."""

import httpx
from typing import List
from urllib.parse import quote

from reference_mcp.providers.base import AbstractProvider
from reference_mcp.models import Reference, ProviderMeta


class DBLPProvider(AbstractProvider):
    """DBLP computer science bibliography provider."""

    NAME = "dblp"
    MAX_PER_QUERY = 100
    TIMEOUT = 4.0

    def __init__(self):
        super().__init__()
        self.base_url = "https://dblp.org/search/publ/api"

    async def search(self, query: str, limit: int) -> List[Reference]:
        """Search DBLP for publications."""
        url = f"{self.base_url}?q={quote(query)}&h={min(limit, self.MAX_PER_QUERY)}&format=json"

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        results = []
        hits = data.get("result", {}).get("hits", {}).get("hit", [])

        for hit in hits:
            info = hit.get("info", {})

            # Extract authors
            authors = []
            author_data = info.get("authors", {}).get("author", [])
            if isinstance(author_data, dict):
                author_data = [author_data]
            for author in author_data:
                if isinstance(author, dict):
                    authors.append(author.get("text", ""))
                else:
                    authors.append(str(author))

            # Extract year
            year = None
            try:
                year = int(info.get("year", ""))
            except (ValueError, TypeError):
                pass

            # Build BibTeX
            bibtex_type = "article" if info.get("type") == "Journal Articles" else "inproceedings"
            bibtex_key = info.get("key", "").split("/")[-1] if info.get("key") else "unknown"

            bibtex_lines = [f"@{bibtex_type}{{{bibtex_key},"]
            bibtex_lines.append(f"  title = {{{info.get('title', '')}}}")
            bibtex_lines.append(f"  author = {{{' and '.join(authors)}}}")
            if year:
                bibtex_lines.append(f"  year = {{{year}}}")
            if info.get("venue"):
                field = "journal" if bibtex_type == "article" else "booktitle"
                bibtex_lines.append(f"  {field} = {{{info.get('venue')}}}")
            if info.get("volume"):
                bibtex_lines.append(f"  volume = {{{info.get('volume')}}}")
            if info.get("pages"):
                bibtex_lines.append(f"  pages = {{{info.get('pages')}}}")
            if info.get("doi"):
                bibtex_lines.append(f"  doi = {{{info.get('doi')}}}")
            bibtex_lines.append("}")

            bibtex = ",\n".join(bibtex_lines)

            # Create reference
            ref = Reference(
                title=info.get("title", ""),
                authors=authors,
                year=year,
                doi=info.get("doi"),
                dblp_key=info.get("key"),
                venue=info.get("venue"),
                volume=info.get("volume"),
                pages=info.get("pages"),
                bibtex=bibtex,
                sources=[
                    ProviderMeta(
                        name=self.NAME,
                        relevance_score=float(hit.get("@score", 0)),
                        url=info.get("url"),
                        raw_data=hit,
                    )
                ],
                score=float(hit.get("@score", 0)),
            )

            results.append(ref)

        return results
