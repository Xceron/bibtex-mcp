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


async def oauth_config(request):
    return JSONResponse({
        "issuer":      request.url.scheme + "://" + request.url.hostname,
        "authorization_endpoint": None,
        "token_endpoint": None,
        "registration_endpoint": request.url.scheme + "://" +
                                 request.url.hostname + "/register",
        "response_types_supported": [],
        "grant_types_supported": [],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": []
    })

async def register(request):
    return JSONResponse({
        "client_id": "public",
        "registration_access_token": None,
        "token_endpoint_auth_method": "none"
    })


def main():
    """Run the MCP server with streamable-http transport."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")

    mcp_app = mcp.http_app(transport="sse")

    # Create Starlette app with OAuth stub endpoints
    routes = [
        Route("/.well-known/oauth-authorization-server",
              oauth_config, methods=["GET"]),
        Route("/register", register, methods=["POST"]),
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
