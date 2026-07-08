"""WebSocket connection tracking and broadcast."""
import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger("plane-tracker")

# Max time to wait on a single client's send before treating it as dead.
# Prevents one slow/stalled socket from delaying the broadcast to everyone else.
SEND_TIMEOUT = 2.0

# Hard cap on simultaneously connected clients. This is a hobby single-box
# app with no auth, so without a ceiling a client could open unbounded
# WebSocket connections and exhaust memory/file descriptors.
MAX_CONNECTIONS = 200


class ConnectionManager:
    """Tracks connected WebSocket clients and broadcasts updates."""

    def __init__(self, max_connections: int = MAX_CONNECTIONS):
        self._connections: set[WebSocket] = set()
        self._max_connections = max_connections

    async def connect(self, ws: WebSocket) -> bool:
        """Accept the connection and register it, unless the server is
        already at capacity, in which case it's accepted-then-closed
        (WebSockets must be accepted before they can be closed with a
        specific code/reason) and False is returned."""
        await ws.accept()
        if len(self._connections) >= self._max_connections:
            logger.warning(
                f"Rejecting WebSocket connection: at capacity ({self._max_connections})"
            )
            await ws.close(code=1013, reason="Server busy, try again later")
            return False
        self._connections.add(ws)
        return True

    def disconnect(self, ws: WebSocket):
        self._connections.discard(ws)

    async def _send(self, ws: WebSocket, message: dict) -> None:
        await asyncio.wait_for(ws.send_json(message), timeout=SEND_TIMEOUT)

    async def broadcast(self, message: dict):
        """Send to all clients concurrently so one slow client can't delay
        the rest; any that time out or error are dropped."""
        connections = list(self._connections)
        if not connections:
            return
        results = await asyncio.gather(
            *(self._send(ws, message) for ws in connections),
            return_exceptions=True,
        )
        for ws, result in zip(connections, results):
            if isinstance(result, asyncio.TimeoutError):
                logger.warning("WebSocket send timed out; dropping slow client")
                self.disconnect(ws)
            elif isinstance(result, Exception):
                self.disconnect(ws)
