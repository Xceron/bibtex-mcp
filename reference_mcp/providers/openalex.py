"""OpenAlex provider implementation."""

import httpx
from typing import List, Optional
from urllib.parse import quote

from reference_mcp.providers.base import AbstractProvider
from reference_mcp.models import Reference, ProviderMeta


class OpenAlexProvider(AbstractProvider):
    """OpenAlex open bibliographic database provider."""

    NAME = "openalex"
    MAX_PER_QUERY = 100
    TIMEOUT = 4.0

    def __init__(self):
        super().__init__()
        self.base_url = "https://api.openalex.org"

    async def search(
        self, query: str, limit: int, year: Optional[int] = None, author: Optional[str] = None
    ) -> List[Reference]:
        """Search OpenAlex for works."""
        # Build filters
        filters = ["concepts.id:C41008148", f'display_name.search:"{query}"']  # Computer Science filter

        # Add year filter if provided
        if year:
            filters.append(f"publication_year:>{year - 1}")  # Greater than or equal to year

        # Add author filter if provided
        if author:
            filters.append(f'authorships.author.display_name.search:"{author}"')

        # Combine all filters
        filter_param = ",".join(filters)

        url = (
            f"{self.base_url}/works?"
            f"filter={quote(filter_param)}"
            f"&per-page={min(limit, self.MAX_PER_QUERY)}"
            f"&select=id,doi,title,authorships,publication_year,primary_location,"
            f"biblio,type"
        )

        headers = {"User-Agent": "ReferenceMCP/1.0 (mailto:your-email@example.com)"}

        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        results = []

        for work in data.get("results", []):
            # Extract authors
            authors = []
            for authorship in work.get("authorships", []):
                author = authorship.get("author", {})
                if author.get("display_name"):
                    authors.append(author["display_name"])

            # Extract year
            year = work.get("publication_year")

            # Extract DOI
            doi = work.get("doi")
            if doi:
                doi = doi.replace("https://doi.org/", "")

            # Extract venue info
            venue = None
            volume = None
            issue = None
            pages = None

            location = work.get("primary_location", {})
            if location:
                source = location.get("source", {})
                if source:
                    venue = source.get("display_name")

            biblio = work.get("biblio", {})
            if biblio:
                volume = biblio.get("volume")
                issue = biblio.get("issue")
                first_page = biblio.get("first_page")
                last_page = biblio.get("last_page")
                if first_page and last_page:
                    pages = f"{first_page}-{last_page}"
                elif first_page:
                    pages = first_page

            # Build BibTeX
            bibtex_type = "article" if work.get("type") == "article" else "inproceedings"
            openalex_id = work.get("id", "").split("/")[-1] if work.get("id") else "unknown"
            bibtex_key = f"openalex_{openalex_id}"

            bibtex_lines = [
                f"@{bibtex_type}{{{bibtex_key},",
                f"  title = {{{work.get('title', '')}}}",
                f"  author = {{{' and '.join(authors)}}}",
            ]
            if year:
                bibtex_lines.append(f"  year = {{{year}}}")
            if venue:
                field = "journal" if bibtex_type == "article" else "booktitle"
                bibtex_lines.append(f"  {field} = {{{venue}}}")
            if volume:
                bibtex_lines.append(f"  volume = {{{volume}}}")
            if issue:
                bibtex_lines.append(f"  number = {{{issue}}}")
            if pages:
                bibtex_lines.append(f"  pages = {{{pages}}}")
            if doi:
                bibtex_lines.append(f"  doi = {{{doi}}}")
            bibtex_lines.append("}")

            bibtex = ",\n".join(bibtex_lines)

            # Create reference
            ref = Reference(
                title=work.get("title", ""),
                authors=authors,
                year=year,
                doi=doi,
                venue=venue,
                volume=volume,
                issue=issue,
                pages=pages,
                bibtex=bibtex,
                sources=[ProviderMeta(name=self.NAME, url=work.get("id"), raw_data=work)],
            )

            results.append(ref)

        return results
