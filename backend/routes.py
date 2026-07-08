"""FastAPI route registration."""
import logging
import time
from collections import deque
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from connection_manager import ConnectionManager
from tracker import AircraftTracker

logger = logging.getLogger("plane-tracker")

# Resolved relative to this file so the app works regardless of the
# process's current working directory.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# We don't expect client messages at all (the client only receives), so any
# steady stream of them is either a bug or abuse. This caps how many we'll
# tolerate before dropping the connection, independent of the server-wide
# MAX_CONNECTIONS cap in ConnectionManager.
MAX_CLIENT_MESSAGES_PER_MINUTE = 30
RATE_WINDOW_SECONDS = 60.0


def register_routes(app: FastAPI, tracker: AircraftTracker, manager: ConnectionManager):
    """Attach API, WebSocket, and static frontend routes to the FastAPI app."""

    @app.get("/api/aircraft")
    async def get_aircraft():
        return tracker.build_payload()

    @app.get("/api/health")
    async def health():
        return {"status": "ok", "tracking": len(tracker.state["aircraft"])}

    @app.websocket("/ws")
    async def websocket_endpoint(ws: WebSocket):
        if not await manager.connect(ws):
            return  # rejected: at capacity, already closed by the manager
        # Send current state immediately on connect
        await ws.send_json(tracker.build_payload())
        message_times: deque[float] = deque()
        try:
            while True:
                # We don't expect client messages; just keep alive, but
                # guard against a client flooding us with junk frames.
                await ws.receive_text()
                now = time.monotonic()
                message_times.append(now)
                while message_times and now - message_times[0] > RATE_WINDOW_SECONDS:
                    message_times.popleft()
                if len(message_times) > MAX_CLIENT_MESSAGES_PER_MINUTE:
                    logger.warning("WebSocket client exceeded message rate limit; disconnecting")
                    break
        except WebSocketDisconnect:
            pass
        except Exception:
            pass
        finally:
            manager.disconnect(ws)

    # Serve frontend static files (mounted last so /api routes take priority)
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def index():
        return FileResponse(str(FRONTEND_DIR / "index.html"))
