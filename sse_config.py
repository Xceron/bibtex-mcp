"""SSE Configuration and Utilities for MCP Server."""

import asyncio
import logging
from typing import AsyncGenerator, Optional
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


class SSEConnection:
    """Manages SSE connection state and heartbeat."""

    def __init__(self, session_id: str, timeout: float = 30.0):
        self.session_id = session_id
        self.timeout = timeout
        self.last_activity = datetime.now(UTC)
        self.is_alive = True
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def start_heartbeat(self) -> AsyncGenerator[str, None]:
        """Generate SSE heartbeat events."""
        while self.is_alive:
            try:
                # Send heartbeat every 15 seconds
                await asyncio.sleep(15)
                self.last_activity = datetime.now(UTC)
                yield f'event: heartbeat\ndata: {{"timestamp": "{self.last_activity.isoformat()}", "session_id": "{self.session_id}"}}\nretry: 15000\n\n'
                logger.debug(f"Heartbeat sent for session {self.session_id}")
            except asyncio.CancelledError:
                self.is_alive = False
                logger.info(f"Heartbeat cancelled for session {self.session_id}")
                break
            except Exception as e:
                logger.error(f"Heartbeat error for session {self.session_id}: {e}")
                self.is_alive = False
                break

    def close(self):
        """Close the connection and cleanup."""
        self.is_alive = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()


class SSEManager:
    """Manages multiple SSE connections."""

    def __init__(self):
        self.connections: dict[str, SSEConnection] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def add_connection(self, session_id: str) -> SSEConnection:
        """Add a new SSE connection."""
        conn = SSEConnection(session_id)
        self.connections[session_id] = conn
        logger.info(f"Added SSE connection for session {session_id}")

        # Start cleanup task if not running
        if not self._cleanup_task or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_stale_connections())

        return conn

    def remove_connection(self, session_id: str):
        """Remove an SSE connection."""
        if session_id in self.connections:
            self.connections[session_id].close()
            del self.connections[session_id]
            logger.info(f"Removed SSE connection for session {session_id}")

    def get_connection(self, session_id: str) -> Optional[SSEConnection]:
        """Get a connection by session ID."""
        return self.connections.get(session_id)

    async def _cleanup_stale_connections(self):
        """Periodically clean up stale connections."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                now = datetime.now(UTC)
                stale_sessions = []

                for session_id, conn in self.connections.items():
                    age = (now - conn.last_activity).total_seconds()
                    if age > conn.timeout * 2:  # Double timeout for cleanup
                        stale_sessions.append(session_id)

                for session_id in stale_sessions:
                    logger.warning(f"Cleaning up stale session: {session_id}")
                    self.remove_connection(session_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")


# Global SSE manager instance
sse_manager = SSEManager()


def create_sse_response_headers() -> dict:
    """Create standard SSE response headers."""
    return {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable Nginx buffering
        "X-Content-Type-Options": "nosniff",
        "Transfer-Encoding": "chunked",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Expose-Headers": "*",
    }


async def sse_error_event(error: str, details: Optional[dict] = None) -> str:
    """Create an SSE error event."""
    error_data = {
        "error": error,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if details:
        error_data.update(details)

    import json

    return f"event: error\ndata: {json.dumps(error_data)}\n\n"


def validate_sse_request(headers: dict) -> bool:
    """Validate if the request is a proper SSE request."""
    accept = headers.get("accept", "").lower()
    return "text/event-stream" in accept or "application/x-ndjson" in accept
