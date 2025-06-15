"""Main entry point for running the MCP server."""

import sys
from reference_mcp.server_runner import run_server


def main():
    """Run the MCP server with custom endpoints."""
    # Check if running with SSE transport (default for remote connections)
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run with stdio transport for local Claude Desktop
        from reference_mcp.server import mcp

        mcp.run()
    else:
        # Run with SSE transport and custom endpoints for remote connections
        run_server()


if __name__ == "__main__":
    main()
