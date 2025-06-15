"""Provider registry for managing different academic database providers."""

from typing import List, Optional
from reference_mcp.providers.base import AbstractProvider


def get_providers(provider_names: Optional[List[str]] = None) -> List[AbstractProvider]:
    """Get list of provider instances based on names."""
    from reference_mcp.providers.dblp import DBLPProvider
    from reference_mcp.providers.semantic_scholar import SemanticScholarProvider
    from reference_mcp.providers.arxiv import ArxivProvider
    from reference_mcp.providers.openalex import OpenAlexProvider

    all_providers = {
        "dblp": DBLPProvider(),
        "semantic_scholar": SemanticScholarProvider(),
        "arxiv": ArxivProvider(),
        "openalex": OpenAlexProvider(),
    }

    if provider_names:
        return [all_providers[name] for name in provider_names if name in all_providers]

    return list(all_providers.values())
