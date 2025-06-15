#!/usr/bin/env python3
"""Minimal MCP server runner with streamable-http transport and OAuth stubs."""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from reference_mcp.server import mcp


# Minimal OAuth stub endpoints
async def oauth_config(request):
    return Response(status_code=404)


async def register(request):
    """Registration endpoint - no registration required."""
    return JSONResponse({"client_id": "public", "registration_access_token": None})


def main():
    """Run the MCP server with streamable-http transport."""
    # Get configuration from environment with defaults
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")

    # Create FastMCP app with SSE
    mcp_app = mcp.http_app(transport="sse")

    # Create Starlette app with OAuth stub endpoints
    routes = [
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
