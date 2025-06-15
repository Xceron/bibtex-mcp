"""Pydantic models for the reference MCP server."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class SearchInput(BaseModel):
    """Input model for search queries."""

    query: str = Field(..., description="Free-text search string")
    max_results: int = Field(20, ge=1, le=100, description="Maximum total references to return")
    providers: Optional[List[str]] = Field(None, description="Optional subset of provider names to search")


class ProviderMeta(BaseModel):
    """Metadata from a specific provider about a reference."""

    name: str = Field(..., description="Provider name (e.g., 'dblp', 'semantic_scholar')")
    relevance_score: Optional[float] = Field(None, description="Provider-specific relevance score")
    url: Optional[str] = Field(None, description="Direct URL to this reference on provider")
    raw_data: Optional[Dict[str, Any]] = Field(None, description="Raw response data from provider")


class Reference(BaseModel):
    """Academic reference with rich metadata and BibTeX representation."""

    model_config = ConfigDict(json_encoders={datetime: lambda v: v.isoformat()})

    # Core identifiers
    title: str = Field(..., description="Paper title")
    authors: List[str] = Field(..., description="List of author names")
    year: Optional[int] = Field(None, description="Publication year")

    # External identifiers
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    arxiv_id: Optional[str] = Field(None, description="arXiv identifier")
    s2_paper_id: Optional[str] = Field(None, description="Semantic Scholar paper ID")
    dblp_key: Optional[str] = Field(None, description="DBLP key")

    # Publication details
    venue: Optional[str] = Field(None, description="Journal/conference name")
    volume: Optional[str] = Field(None, description="Journal volume")
    issue: Optional[str] = Field(None, description="Journal issue")
    pages: Optional[str] = Field(None, description="Page numbers")
    publisher: Optional[str] = Field(None, description="Publisher name")

    # Content
    abstract: Optional[str] = Field(None, description="Paper abstract")
    bibtex: str = Field(..., description="BibTeX-formatted citation")
    citation_count: Optional[int] = Field(None, description="Number of citations")

    # Provider info
    sources: List[ProviderMeta] = Field(
        default_factory=list, description="List of providers that returned this reference"
    )

    # Aggregated score
    score: float = Field(0.0, description="Aggregated relevance score across providers")

    def merge_with(self, other: "Reference") -> None:
        """Merge another reference into this one, keeping most complete data."""
        # Prefer non-None values
        if not self.doi and other.doi:
            self.doi = other.doi
        if not self.arxiv_id and other.arxiv_id:
            self.arxiv_id = other.arxiv_id
        if not self.s2_paper_id and other.s2_paper_id:
            self.s2_paper_id = other.s2_paper_id
        if not self.dblp_key and other.dblp_key:
            self.dblp_key = other.dblp_key

        # Merge author lists (keep first if different)
        if not self.authors and other.authors:
            self.authors = other.authors

        # Merge abstract (prefer longer one)
        if other.abstract:
            if not self.abstract or len(other.abstract) > len(self.abstract):
                self.abstract = other.abstract

        # Merge citation count (prefer higher)
        if other.citation_count:
            if not self.citation_count or other.citation_count > self.citation_count:
                self.citation_count = other.citation_count

        # Add all sources
        self.sources.extend(other.sources)

        # Recalculate score as average of all provider scores
        provider_scores = [s.relevance_score for s in self.sources if s.relevance_score is not None]
        if provider_scores:
            self.score = sum(provider_scores) / len(provider_scores)
