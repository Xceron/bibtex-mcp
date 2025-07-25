# BibTeX MCP Server

Multi-provider academic reference search with BibTeX generation. Searches arXiv, DBLP, Semantic Scholar, and OpenAlex concurrently.

## MCP Client Configuration

For Claude Desktop, ChatGPT, or other MCP clients:
- **Server URL**: `https://mcp.florianbrand.de/sse`
- **Transport**: SSE (Server-Sent Events)
- **Authentication**: None required

## Installation

### Remote Clients

This server is hosted publicly at: `https://mcp.florianbrand.de/sse`

**Important**: Use the URL exactly as shown above (without www subdomain)

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
