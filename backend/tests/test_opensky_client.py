"""Unit and integration tests for OpenSkyClient."""
import asyncio
import time
from unittest.mock import AsyncMock, Mock

from services.geo import BoundingBox
from services.opensky_client import OpenSkyClient


def make_client() -> OpenSkyClient:
    return OpenSkyClient(client_id="id", client_secret="secret")


def test_parse_state_maps_fields_in_order():
    state = [
        "abc123", "WZZ123  ", "Hungary", 0, 0,
        19.1, 47.5, 10000, False, 200,
        90, 0, None, 10500, "1200", False, 0,
    ]
    parsed = OpenSkyClient._parse_state(state)
    assert parsed["icao24"] == "abc123"
    assert parsed["callsign"] == "WZZ123"
    assert parsed["latitude"] == 47.5
    assert parsed["longitude"] == 19.1
    assert parsed["aircraft_type"] is None
    assert parsed["registration"] is None


def test_parse_state_without_callsign_leaves_it_falsy():
    state = ["abc123", None, "Hungary"] + [None] * 13
    parsed = OpenSkyClient._parse_state(state)
    assert parsed["callsign"] is None


def test_ensure_token_fetches_and_caches():
    client = make_client()
    response = Mock()
    response.raise_for_status = Mock()
    response.json = Mock(return_value={"access_token": "tok1", "expires_in": 1800})
    client._http.post = AsyncMock(return_value=response)

    asyncio.run(client._ensure_token())

    assert client._token == "tok1"
    client._http.post.assert_awaited_once()

    # Second call within the expiry window should not re-fetch.
    asyncio.run(client._ensure_token())
    client._http.post.assert_awaited_once()


def test_ensure_token_refetches_after_expiry():
    client = make_client()
    client._token = "stale"
    client._token_expiry = time.time() - 1  # already expired

    response = Mock()
    response.raise_for_status = Mock()
    response.json = Mock(return_value={"access_token": "fresh", "expires_in": 1800})
    client._http.post = AsyncMock(return_value=response)

    asyncio.run(client._ensure_token())

    assert client._token == "fresh"


def test_fetch_states_returns_parsed_states():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._token = "tok"

    response = Mock()
    response.status_code = 200
    response.raise_for_status = Mock()
    response.json = Mock(return_value={"states": [
        ["abc123", "WZZ123", "Hungary"] + [None] * 13,
    ]})
    client._http.get = AsyncMock(return_value=response)

    box = BoundingBox(lat_min=47.0, lat_max=48.0, lon_min=18.5, lon_max=19.5)
    results = asyncio.run(client.fetch_states(box))

    assert len(results) == 1
    assert results[0]["icao24"] == "abc123"


def test_fetch_states_retries_once_on_401():
    client = make_client()
    client._ensure_token = AsyncMock()
    client._token = "expired"

    unauthorized = Mock()
    unauthorized.status_code = 401

    success = Mock()
    success.status_code = 200
    success.raise_for_status = Mock()
    success.json = Mock(return_value={"states": []})

    client._http.get = AsyncMock(side_effect=[unauthorized, success])

    box = BoundingBox(lat_min=47.0, lat_max=48.0, lon_min=18.5, lon_max=19.5)
    results = asyncio.run(client.fetch_states(box))

    assert results == []
    assert client._http.get.await_count == 2
    assert client._ensure_token.await_count == 2


def test_close_closes_http_client():
    client = make_client()
    client._http.aclose = AsyncMock()
    asyncio.run(client.close())
    client._http.aclose.assert_awaited_once()
