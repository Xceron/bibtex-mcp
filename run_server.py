#!/usr/bin/env python3
"""Minimal MCP server runner with streamable-http transport and OAuth stubs."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
import uvicorn

from reference_mcp.server import mcp


# Minimal OAuth stub endpoints
async def oauth_config(request):
    """OAuth discovery endpoint - indicates no auth required."""
    return JSONResponse({
        "authorization_endpoint": None,
        "token_endpoint": None,
        "scopes_supported": []
    })


async def register(request):
    """Registration endpoint - no registration required."""
    return JSONResponse({
        "client_id": "public",
        "registration_access_token": None
    })


def main():
    """Run the MCP server with streamable-http transport."""
    # Get configuration from environment with defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")

    # Create FastMCP app with streamable-http
    mcp_app = mcp.http_app(transport="streamable-http")
    
    # Create Starlette app with OAuth stub endpoints
    routes = [
        Route("/.well-known/oauth-authorization-server", oauth_config, methods=["GET"]),
        Route("/register", register, methods=["POST"]),
        Mount("/", app=mcp_app),
    ]
    
    app = Starlette(routes=routes)
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
