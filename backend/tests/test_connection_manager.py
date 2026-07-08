"""Unit tests for ConnectionManager's connection cap."""
import asyncio
from unittest.mock import AsyncMock

from connection_manager import ConnectionManager


def make_ws() -> AsyncMock:
    return AsyncMock()


def test_connect_accepts_under_capacity():
    manager = ConnectionManager(max_connections=2)
    ws = make_ws()
    accepted = asyncio.run(manager.connect(ws))
    assert accepted is True
    ws.accept.assert_awaited_once()
    ws.close.assert_not_called()


def test_connect_rejects_over_capacity():
    manager = ConnectionManager(max_connections=1)
    ws1, ws2 = make_ws(), make_ws()

    assert asyncio.run(manager.connect(ws1)) is True
    accepted = asyncio.run(manager.connect(ws2))

    assert accepted is False
    ws2.accept.assert_awaited_once()  # accepted before being rejected/closed
    ws2.close.assert_awaited_once()


def test_disconnect_frees_capacity_for_new_connections():
    manager = ConnectionManager(max_connections=1)
    ws1, ws2 = make_ws(), make_ws()

    asyncio.run(manager.connect(ws1))
    manager.disconnect(ws1)

    assert asyncio.run(manager.connect(ws2)) is True
