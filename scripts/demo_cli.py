#!/usr/bin/env python
"""CLI tool for testing the reference MCP server."""

import asyncio
import json
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent directory to path
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from reference_mcp.models import SearchInput
from reference_mcp.providers.registry import get_providers
from reference_mcp.aggregator import fanout, dedupe_rank

app = typer.Typer()
console = Console()


async def perform_search(query: str, max_results: int, providers: Optional[List[str]]) -> List:
    """Perform the actual search."""
    input_data = SearchInput(query=query, max_results=max_results, providers=providers)

    provider_instances = get_providers(input_data.providers)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Searching {len(provider_instances)} providers...", total=None)

        all_results = await fanout(input_data.query, input_data.max_results, provider_instances)

        progress.update(task, description="Deduplicating and ranking results...")
        final_results = dedupe_rank(all_results, input_data.max_results)

    return final_results


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query string"),
    max_results: int = typer.Option(20, "--max", "-m", help="Maximum results to return"),
    providers: Optional[str] = typer.Option(None, "--providers", "-p", help="Comma-separated provider names"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json, bibtex"),
):
    """Search for academic references across multiple providers."""
    # Parse providers
    provider_list = None
    if providers:
        provider_list = [p.strip() for p in providers.split(",")]

    # Run search
    results = asyncio.run(perform_search(query, max_results, provider_list))

    if format == "json":
        # JSON output
        output = {
            "query": query,
            "total_results": len(results),
            "references": [
                {
                    "title": ref.title,
                    "authors": ref.authors,
                    "year": ref.year,
                    "venue": ref.venue,
                    "doi": ref.doi,
                    "arxiv_id": ref.arxiv_id,
                    "bibtex": ref.bibtex,
                    "score": ref.score,
                    "sources": [src.name for src in ref.sources],
                }
                for ref in results
            ],
        }
        console.print_json(json.dumps(output))

    elif format == "bibtex":
        # BibTeX output
        for ref in results:
            console.print(ref.bibtex)
            console.print()

    else:
        # Table output
        if not results:
            console.print("[yellow]No results found.[/yellow]")
            return

        table = Table(title=f"Search Results for: {query}")
        table.add_column("Title", style="cyan", overflow="fold")
        table.add_column("Authors", style="green")
        table.add_column("Year", style="yellow")
        table.add_column("Venue", style="blue")
        table.add_column("Sources", style="magenta")
        table.add_column("Score", style="red")

        for ref in results:
            authors_str = "; ".join(ref.authors[:3])
            if len(ref.authors) > 3:
                authors_str += f" +{len(ref.authors) - 3}"

            sources_str = ", ".join(src.name for src in ref.sources)

            table.add_row(
                ref.title[:80] + ("..." if len(ref.title) > 80 else ""),
                authors_str,
                str(ref.year) if ref.year else "N/A",
                ref.venue[:30] if ref.venue else "N/A",
                sources_str,
                f"{ref.score:.2f}",
            )

        console.print(table)
        console.print(f"\n[bold]Total results:[/bold] {len(results)}")


@app.command()
def providers():
    """List available providers."""
    all_providers = get_providers()

    table = Table(title="Available Providers")
    table.add_column("Name", style="cyan")
    table.add_column("Max Results", style="yellow")
    table.add_column("Timeout (s)", style="green")

    for provider in all_providers:
        table.add_row(provider.NAME, str(provider.MAX_PER_QUERY), str(provider.TIMEOUT))

    console.print(table)


if __name__ == "__main__":
    app()
