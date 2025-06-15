# BibTeX MCP Server

Multi-provider academic reference search with BibTeX generation. Searches arXiv, DBLP, Semantic Scholar, and OpenAlex concurrently.

## Installation

### Remote Clients

This server is hosted publicly under www.mcp.florianbrand.de/sse

### Local Clients

If you prefer to run the server locally, you can add it the following way:
```json
{
  "mcpServers": {
    "bibtex": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/bibtex-mcp", "python", "-m", "reference_mcp", "--stdio"],
      "env": {
        "SEMANTIC_SCHOLAR_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

A semantic scholar API key is optional but recommended for higher rate limits. It can be requested [here](https://www.semanticscholar.org/product/api).
