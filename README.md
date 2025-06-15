# BibTeX MCP Server

A Model Context Protocol (MCP) server that provides academic reference search and BibTeX generation from multiple scholarly databases.

## Overview

This MCP server searches across multiple academic databases concurrently to find research papers and returns properly formatted BibTeX citations. It automatically deduplicates results and merges data from different sources to provide comprehensive bibliographic information.

## Supported Providers

- **ArXiv** - Preprint repository for physics, mathematics, computer science, and related fields
- **DBLP** - Computer science bibliography database
- **Semantic Scholar** - AI-powered academic search engine
- **OpenAlex** - Open scholarly database

## Features

- **Multi-provider search** - Searches all databases concurrently for comprehensive results
- **Automatic deduplication** - Merges duplicate papers found across different databases
- **BibTeX generation** - Returns properly formatted BibTeX entries for each paper
- **Relevance ranking** - Sorts results by relevance score, publication year, and other factors
- **Configurable providers** - Option to search specific databases only

## Installation

### Using FastMCP (Recommended)

```bash
fastmcp install mcp_server.py --with httpx --with pydantic --with rapidfuzz
```

### Manual Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bibtex-mcp
```

2. Install dependencies:
```bash
uv sync
```

3. Run the server:
```bash
# Run the enhanced server with better SSE handling
python run_server.py

# Or run as a package
python -m reference_mcp

# Or run the standalone server
python mcp_server.py
```

### Testing SSE Connection

Test the SSE connection to ensure it's working properly:

```bash
# Test SSE endpoint
curl -H "Accept: text/event-stream" http://localhost:8000/sse-test

# Test health check
curl http://localhost:8000/health

# Run comprehensive tests
python test_sse_client.py
```

## Usage

### MCP Tool

The server provides a single tool:

**`searchReference`**
- **Description**: Search multiple CS/AI literature databases and return BibTeX entries
- **Parameters**:
  - `query` (string, required): Free-text search string for finding papers
  - `max_results` (integer, optional): Maximum number of references to return (1-100, default 20)
  - `providers` (array, optional): List of provider names to search. Available: `["arxiv", "dblp", "semantic_scholar", "openalex"]`

### Example Response

```json
{
  "references": [
    {
      "title": "Attention Is All You Need",
      "authors": ["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
      "year": 2017,
      "doi": "10.48550/arXiv.1706.03762",
      "arxiv_id": "1706.03762",
      "venue": "NIPS",
      "bibtex": "@inproceedings{vaswani2017attention,\n  title = {Attention Is All You Need},\n  author = {Ashish Vaswani and Noam Shazeer and Niki Parmar and Jakob Uszkoreit and Llion Jones and Aidan N. Gomez and Lukasz Kaiser and Illia Polosukhin},\n  year = {2017},\n  booktitle = {Advances in Neural Information Processing Systems},\n  pages = {5998--6008}\n}",
      "sources": [
        {
          "name": "arxiv",
          "url": "https://arxiv.org/abs/1706.03762"
        },
        {
          "name": "dblp", 
          "url": "https://dblp.org/rec/conf/nips/VaswaniSPUJGKP17"
        }
      ]
    }
  ],
  "total_found": 1,
  "providers_used": ["arxiv", "dblp", "semantic_scholar", "openalex"]
}
```

## Configuration

### Environment Variables

You can set environment variables either directly or using a `.env` file in the project root.

#### Using .env file (recommended)

1. Copy the example file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your API key:
```bash
# Semantic Scholar API Key (optional but recommended for higher rate limits)
# Get your API key from: https://www.semanticscholar.org/product/api
SEMANTIC_SCHOLAR_API_KEY=your_actual_api_key_here
```

#### Supported Variables

- `SEMANTIC_SCHOLAR_API_KEY` (optional): API key for Semantic Scholar to increase rate limits and avoid throttling

### Provider Selection

You can limit searches to specific providers by passing the `providers` parameter:

```json
{
  "query": "transformer neural networks",
  "max_results": 10,
  "providers": ["arxiv", "dblp"]
}
```

## Technical Details

### Deduplication Strategy

The server uses multiple strategies to identify and merge duplicate papers:

1. **Hard identifiers**: DOI, ArXiv ID, Semantic Scholar paper ID
2. **Fuzzy matching**: Title similarity (94%+ threshold) + author matching + year consistency
3. **Data merging**: Combines the best data from each source (non-null values, longer abstracts, etc.)

### BibTeX Format

Generated BibTeX entries include:
- Standard fields: `title`, `author`, `year`
- Publication details: `journal`/`booktitle`, `volume`, `pages`, `doi`
- ArXiv specific: `eprint`, `archivePrefix`, `primaryClass`
- Proper entry types: `@article`, `@inproceedings` based on publication type

### Rate Limiting & Timeouts

- Each provider has configurable timeout limits
- Failed providers don't block other searches
- Simple in-memory caching to reduce API calls

## Development

### Project Structure

```
bibtex-mcp/
├── reference_mcp/           # Main package
│   ├── models.py           # Pydantic data models
│   ├── server.py          # MCP server implementation
│   ├── aggregator.py      # Deduplication and ranking logic
│   └── providers/         # Database provider implementations
│       ├── base.py        # Abstract provider class
│       ├── arxiv.py       # ArXiv provider
│       ├── dblp.py        # DBLP provider
│       ├── semantic_scholar.py  # Semantic Scholar provider
│       └── openalex.py    # OpenAlex provider
├── mcp_server.py          # Standalone server for fastmcp
├── test_basic.py          # Basic functionality tests
└── README.md
```

### Running Tests

```bash
python test_basic.py
```

## Troubleshooting

### SSE Connection Issues

If you're experiencing "SSE connection not established" errors:

1. **Check SSE endpoint availability**:
```bash
curl -H "Accept: text/event-stream" http://localhost:8000/sse-test
```

2. **Verify server is running**:
```bash
curl http://localhost:8000/health
```

3. **Common fixes**:
- Ensure no proxy/firewall is blocking SSE connections
- Check that the server is binding to the correct host/port
- Verify CORS headers are properly configured
- Disable buffering in reverse proxies (nginx: `proxy_buffering off`)

4. **For Docker deployments**:
- Ensure port 8000 is properly exposed
- Check container logs: `docker logs <container-id>`
- Verify network connectivity between client and server

### MCP Inspector Issues

The MCP Inspector expects SSE transport. If using STDIO transport locally, you may see connection errors. Solutions:

1. Use the enhanced server (`run_server.py`) which properly implements SSE
2. Test with the provided `test_sse_client.py` script
3. Use alternative MCP clients that support STDIO transport

### Provider-Specific Issues

- **Semantic Scholar**: May require API key for higher rate limits
- **OpenAlex**: Filters results to Computer Science domain
- **ArXiv**: Limited to 100 results per query
- **DBLP**: Best for computer science publications

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=debug python run_server.py
```

### Adding New Providers

1. Create a new provider class inheriting from `AbstractProvider`
2. Implement the `search()` method
3. Add to the provider registry in `get_providers()`

Example provider implementation:

```python
class NewProvider(AbstractProvider):
    NAME = "new_provider"
    MAX_PER_QUERY = 50
    TIMEOUT = 3.0
    
    async def search(self, query: str, limit: int) -> List[Reference]:
        # Implement search logic
        # Return list of Reference objects
        pass
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **Import errors**: Use the standalone `mcp_server.py` file for fastmcp installation
2. **Rate limiting**: Set `SEMANTIC_SCHOLAR_API_KEY` environment variable or create a `.env` file with your API key
3. **Environment variables not loading**: Ensure `.env` file is in the project root directory and contains valid key-value pairs
4. **Timeout errors**: Individual provider failures don't affect other providers
5. **Empty results**: Try broader search terms or different providers

### Debug Mode

Run with environment variable `DEBUG=1` for verbose logging:

```bash
DEBUG=1 python -m reference_mcp
```