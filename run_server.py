#!/usr/bin/env python3
"""Minimal MCP server runner with streamable-http transport and OAuth stubs."""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from reference_mcp.server import mcp

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# Minimal OAuth stub endpoints
async def oauth_config(request):
    return Response(status_code=404)


async def register(request):
    """Registration endpoint - no registration required."""
    return JSONResponse({"client_id": "public", "registration_access_token": None})


async def health(request):
    """Health check endpoint for Docker health checks."""
    return JSONResponse({"status": "healthy", "service": "bibtex-mcp"})


def main():
    """Run the MCP server with streamable-http transport."""
    # Get configuration from environment with defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")

    logger.info(f"Starting MCP server on {host}:{port}")

    # Create FastMCP app with SSE
    try:
        mcp_app = mcp.http_app(transport="sse")
        logger.info("Successfully created MCP app with SSE transport")
        logger.info("Available tools: search_reference, search, fetch")
    except Exception as e:
        logger.error(f"Failed to create MCP app: {e}")
        raise

    # Create Starlette app with OAuth stub endpoints
    routes = [
        Route("/health", health),
        Route("/.well-known/oauth-authorization-server", oauth_config),
        Mount("/", app=mcp_app),
    ]

    app = Starlette(routes=routes)

    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=False
    )
    # Run with uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
