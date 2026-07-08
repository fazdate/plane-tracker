"""Integration tests for the FastAPI routes (HTTP + WebSocket), exercising
routes.py wired up with a real ConnectionManager and a fake tracker."""
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from connection_manager import ConnectionManager
from routes import register_routes


def make_app(tracker=None, manager=None):
    app = FastAPI()
    tracker = tracker or Mock(
        build_payload=Mock(return_value={"count": 0, "aircraft": []}),
        state={"aircraft": []},
    )
    manager = manager or ConnectionManager()
    register_routes(app, tracker, manager)
    return app, tracker, manager


def test_get_aircraft_returns_tracker_payload():
    payload = {"count": 2, "aircraft": [{"icao24": "abc"}]}
    tracker = Mock(build_payload=Mock(return_value=payload), state={"aircraft": []})
    app, _, _ = make_app(tracker=tracker)

    with TestClient(app) as client:
        resp = client.get("/api/aircraft")

    assert resp.status_code == 200
    assert resp.json() == payload


def test_health_reports_tracked_count():
    tracker = Mock(
        build_payload=Mock(return_value={}),
        state={"aircraft": [{"icao24": "a"}, {"icao24": "b"}]},
    )
    app, _, _ = make_app(tracker=tracker)

    with TestClient(app) as client:
        resp = client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "tracking": 2}


def test_index_serves_frontend_html():
    app, _, _ = make_app()

    with TestClient(app) as client:
        resp = client.get("/")

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_websocket_receives_initial_payload_on_connect():
    payload = {"count": 0, "aircraft": []}
    tracker = Mock(build_payload=Mock(return_value=payload), state={"aircraft": []})
    app, _, _ = make_app(tracker=tracker)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            data = ws.receive_json()

    assert data == payload


def test_websocket_rejected_when_manager_at_capacity():
    manager = ConnectionManager(max_connections=1)
    app, _, _ = make_app(manager=manager)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as first:
            first.receive_json()  # initial payload

            with client.websocket_connect("/ws") as second:
                # Server accepts then immediately closes at-capacity sockets.
                with pytest.raises(WebSocketDisconnect):
                    second.receive_json()


def test_websocket_disconnect_frees_manager_slot():
    manager = ConnectionManager(max_connections=5)
    app, _, _ = make_app(manager=manager)

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            assert len(manager._connections) == 1

    assert len(manager._connections) == 0
