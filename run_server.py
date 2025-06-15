#!/usr/bin/env python3
"""Minimal MCP server runner with streamable-http transport."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from reference_mcp.server import mcp


def main():
    """Run the MCP server with streamable-http transport."""
    # Get configuration from environment with defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_PATH", "/mcp")
    log_level = os.getenv("LOG_LEVEL", "info")

    # Run server with streamable-http transport
    mcp.run(
        transport="streamable-http",
        host=host,
        port=port,
        path=path,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
