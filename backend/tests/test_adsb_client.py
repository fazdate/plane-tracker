"""Unit and integration tests for AdsbLolClient."""
import asyncio
from unittest.mock import AsyncMock, Mock

from services.adsb_client import AdsbLolClient
from services.geo import BoundingBox


def test_normalize_airborne_aircraft():
    raw = {
        "hex": "ABC123",
        "flight": "WZZ123  ",
        "lat": 47.5,
        "lon": 19.1,
        "alt_baro": 35000,
        "gs": 450,
        "baro_rate": 1000,
        "track": 270,
        "squawk": "1200",
        "t": "B738",
        "r": "HA-LVK",
    }
    norm = AdsbLolClient._normalize(raw)
    assert norm["icao24"] == "abc123"
    assert norm["callsign"] == "WZZ123"
    assert norm["on_ground"] is False
    assert round(norm["baro_altitude"], 2) == round(35000 * 0.3048, 2)
    assert round(norm["velocity"], 4) == round(450 * 0.514444, 4)
    assert round(norm["vertical_rate"], 5) == round(1000 * 0.00508, 5)
    assert norm["aircraft_type"] == "B738"
    assert norm["registration"] == "HA-LVK"


def test_normalize_ground_vehicle_altitude():
    raw = {"hex": "abc123", "lat": 1.0, "lon": 2.0, "alt_baro": "ground"}
    norm = AdsbLolClient._normalize(raw)
    assert norm["on_ground"] is True
    assert norm["baro_altitude"] is None


def test_normalize_missing_position_returns_none():
    assert AdsbLolClient._normalize({"hex": "abc123"}) is None
    assert AdsbLolClient._normalize({"hex": "abc123", "lat": 1.0}) is None


def test_normalize_missing_hex_defaults_to_empty_string():
    norm = AdsbLolClient._normalize({"lat": 1.0, "lon": 2.0})
    assert norm["icao24"] == ""


def test_box_to_radius_nm_covers_box_diagonal():
    client = AdsbLolClient(center_lat=47.5, center_lon=19.1)
    box = BoundingBox(lat_min=47.0, lat_max=48.0, lon_min=18.5, lon_max=19.5)
    radius = client._box_to_radius_nm(box)
    assert radius >= 1
    assert isinstance(radius, int)


def test_fetch_states_filters_to_bounding_box():
    client = AdsbLolClient(center_lat=47.5, center_lon=19.1)
    box = BoundingBox(lat_min=47.0, lat_max=48.0, lon_min=18.5, lon_max=19.5)

    payload = {
        "ac": [
            {"hex": "in1", "flight": "AAA1", "lat": 47.5, "lon": 19.1, "alt_baro": 1000},
            {"hex": "out1", "flight": "BBB1", "lat": 60.0, "lon": 19.1, "alt_baro": 1000},
            {"hex": "noloc", "flight": "CCC1"},
        ]
    }
    response = Mock()
    response.raise_for_status = Mock()
    response.json = Mock(return_value=payload)
    client._http.get = AsyncMock(return_value=response)

    results = asyncio.run(client.fetch_states(box))

    assert len(results) == 1
    assert results[0]["icao24"] == "in1"


def test_close_closes_http_client():
    client = AdsbLolClient(center_lat=47.5, center_lon=19.1)
    client._http.aclose = AsyncMock()
    asyncio.run(client.close())
    client._http.aclose.assert_awaited_once()
