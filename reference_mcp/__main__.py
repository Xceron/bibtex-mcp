"""Main entry point for running the MCP server."""

import os
import sys
from reference_mcp.server import mcp


def main():
    """Run the MCP server with appropriate transport."""
    # Check if running with stdio transport (for local Claude Desktop)
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        # Run with stdio transport for local Claude Desktop
        mcp.run()
    else:
        # Run with streamable-http transport for remote connections
        mcp.run(
            transport="streamable-http",
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            path=os.getenv("MCP_PATH", "/"),
            log_level=os.getenv("LOG_LEVEL", "info"),
        )


if __name__ == "__main__":
    main()
