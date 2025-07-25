#!/usr/bin/env python3
"""
Production server entry point - runs the MCP server with SSE transport.
"""

import os
import logging
from reference_mcp.server import create_server

# Configure logging
logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Run the MCP server."""
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8000))

    logger.info(f"Starting server on {host}:{port}")

    try:
        # Create and run the server
        server = create_server()
        server.run(transport="sse", host=host, port=port)
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        raise


if __name__ == "__main__":
    main()