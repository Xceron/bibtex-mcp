"""Server runner for the reference MCP server."""

import os
from .server import mcp


def run_server(host="0.0.0.0", port=8000):
    """Run the server with streamable-http transport for remote access."""
    # Run with streamable-http transport
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        path=os.getenv("MCP_PATH", "/mcp"),
        log_level=os.getenv("LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    run_server()
