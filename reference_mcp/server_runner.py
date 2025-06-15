"""Server runner with custom endpoints for the reference MCP server."""

import logging
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
import uvicorn

from .server import mcp

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# OAuth discovery endpoints
async def oauth_config(request):
    """OAuth2 discovery endpoint - indicates no auth required."""
    return JSONResponse({"authorization_endpoint": None, "token_endpoint": None, "scopes_supported": []})


async def register(request):
    """Registration endpoint - no registration required."""
    return JSONResponse({"client_id": "public", "registration_access_token": None})


async def health_check(request):
    """Health check endpoint for monitoring."""
    return JSONResponse({"status": "healthy", "service": "reference-mcp"})


async def sse_health(request):
    """SSE-specific health check."""

    async def event_generator():
        yield 'event: ping\ndata: {"status":"ok"}\n\n'

    return Response(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


def create_app():
    """Create the Starlette application with all routes."""
    # Get the MCP app (SSE transport)
    logger.info("Creating MCP app with SSE transport")
    mcp_app = mcp.http_app(transport="sse")

    # Create main app with OAuth routes
    routes = [
        Route("/.well-known/oauth-authorization-server", oauth_config, methods=["GET"]),
        Route("/register", register, methods=["POST"]),
        Route("/health", health_check, methods=["GET"]),
        Route("/sse-health", sse_health, methods=["GET"]),
    ]

    app = Starlette(routes=routes)

    # Add CORS middleware for SSE support
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Mount the MCP app
    app.router.routes.append(Mount("/", app=mcp_app))

    # Add startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("MCP server starting up...")
        logger.info("SSE endpoint available at: /sse")
        logger.info("Message endpoint available at: /messages")

    return app


def run_server(host="0.0.0.0", port=8000):
    """Run the server with SSE transport for remote access."""
    app = create_app()
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="debug",
        access_log=True,
        # Disable buffering for SSE
        server_header=False,
        date_header=False,
    )


if __name__ == "__main__":
    run_server()
