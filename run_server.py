#!/usr/bin/env python3
"""Enhanced MCP server runner with improved SSE handling."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from reference_mcp.server import mcp
from sse_config import sse_manager, create_sse_response_headers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("mcp_server.log")],
)
logger = logging.getLogger(__name__)


# OAuth endpoints
async def oauth_config(request):
    """OAuth2 discovery endpoint - indicates no auth required."""
    return JSONResponse({"authorization_endpoint": None, "token_endpoint": None, "scopes_supported": []})


async def register(request):
    """Registration endpoint - no registration required."""
    return JSONResponse({"client_id": "public", "registration_access_token": None})


# Health check endpoints
async def health_check(request):
    """Basic health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "reference-mcp",
            "version": "1.0.0",
            "active_connections": len(sse_manager.connections),
        }
    )


async def sse_test(request):
    """SSE test endpoint for debugging."""

    async def generate():
        yield 'event: test\ndata: {"message": "SSE connection established"}\n\n'
        await asyncio.sleep(1)
        yield 'event: test\ndata: {"message": "SSE working correctly"}\n\n'

    return StreamingResponse(generate(), media_type="text/event-stream", headers=create_sse_response_headers())


# Error handler
async def error_handler(request, exc):
    """Global error handler."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc) if os.getenv("DEBUG") else "An error occurred"},
    )


def create_app():
    """Create the Starlette application with all configurations."""
    # Create MCP app with SSE transport
    logger.info("Creating MCP app with SSE transport")
    mcp_app = mcp.http_app(transport="sse")

    # Define routes
    routes = [
        Route("/.well-known/oauth-authorization-server", oauth_config, methods=["GET"]),
        Route("/register", register, methods=["POST"]),
        Route("/health", health_check, methods=["GET"]),
        Route("/sse-test", sse_test, methods=["GET"]),
    ]

    # Create main app
    app = Starlette(routes=routes, exception_handlers={Exception: error_handler})

    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Only add GZip for non-SSE responses
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Mount MCP app
    app.router.routes.append(Mount("/", app=mcp_app))

    # Startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        logger.info("=" * 50)
        logger.info("MCP Server Starting")
        logger.info("SSE endpoint: /sse")
        logger.info("Message endpoint: /messages")
        logger.info("Health check: /health")
        logger.info("SSE test: /sse-test")
        logger.info("=" * 50)

    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("MCP Server shutting down...")
        # Clean up connections
        for session_id in list(sse_manager.connections.keys()):
            sse_manager.remove_connection(session_id)

    return app


def main():
    """Main entry point."""
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    # Create app
    app = create_app()

    # Configure uvicorn
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level=log_level,
        access_log=True,
        use_colors=True,
        # Important for SSE
        timeout_keep_alive=75,
        timeout_notify=60,
        # Disable buffering
        server_header=False,
        date_header=True,
        # Workers (1 for SSE to maintain connection state)
        workers=1,
        # Enable auto-reload in development
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )

    # Run server
    server = uvicorn.Server(config)

    logger.info(f"Starting server on {host}:{port}")
    server.run()


if __name__ == "__main__":
    main()
