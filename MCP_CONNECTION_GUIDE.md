# MCP Connection Guide for BibTeX Server

## Important: Connection URL

When connecting to this MCP server, you **MUST** use the SSE endpoint:

```
http://localhost:8000/sse
```

**NOT** the base URL (`http://localhost:8000/`) which will return 404.

## Why?

The FastMCP SSE transport creates specific endpoints:
- `GET /sse` - Server-Sent Events stream (where clients connect)
- `POST /messages` - Client-to-server messages

There is no handler at the base URL, which is standard behavior for SSE transport in the MCP protocol.

## Example Client Connection

### Using MCP Python Client

```python
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
import json

async with sse_client("http://localhost:8000/sse") as (read, write):
    async with ClientSession(read, write) as session:
        # Initialize
        await session.initialize()
        
        # Use tools
        result = await session.call_tool(
            name="search_reference",
            arguments={"query": "deep learning", "max_results": 5}
        )
        
        # Parse JSON response
        data = json.loads(result.content[0].text)
```

### For MCP Client Applications

Configure your MCP client with:
- **Server URL**: `http://localhost:8000/sse`
- **Transport**: SSE (Server-Sent Events)
- **Authentication**: None required

## Available Tools

1. **search_reference** - Full academic search with BibTeX
2. **search** - Lightweight search for browsing
3. **fetch** - Retrieve full documents by ID

## Response Format

All tool responses are JSON-serialized in `result.content[0].text`. This is standard MCP protocol behavior.

## Production Deployment

For production with a reverse proxy, you can add a redirect:

```nginx
location = / {
    return 301 /sse;
}
```

Or with Caddy:

```caddyfile
@base {
    path /
}
redir @base /sse permanent
```