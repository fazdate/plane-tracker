"""Unit/integration tests for AircraftTracker's aircraft processing pipeline
(process_aircraft, build_payload, _refresh_once). Complements test_tracker.py,
which covers the failover/backoff state machine."""
import asyncio
from unittest.mock import AsyncMock, Mock

from tracker import AircraftTracker

HOME_LAT, HOME_LON = 47.5, 19.1
FOCUS_KM = 10.0


def make_tracker(**overrides) -> AircraftTracker:
    defaults = dict(
        data_source=Mock(name="data_source"),
        poll_interval=6,
        home_lat=HOME_LAT,
        home_lon=HOME_LON,
        focus_km=FOCUS_KM,
        box=Mock(name="box"),
        alert_engine=Mock(evaluate=Mock(return_value=None)),
        enrichment=Mock(enrich_static=Mock(), get_route=AsyncMock(return_value=None)),
        manager=Mock(broadcast=AsyncMock()),
        daily_stats_db_path=":memory:",
    )
    defaults.update(overrides)
    return AircraftTracker(**defaults)


def make_aircraft(icao24, lat, lon, callsign="TEST123", on_ground=False):
    return {
        "icao24": icao24,
        "callsign": callsign,
        "latitude": lat,
        "longitude": lon,
        "on_ground": on_ground,
    }


def test_process_aircraft_skips_entries_without_position():
    tracker = make_tracker()
    raw = [{"icao24": "abc", "callsign": "TEST1", "latitude": None, "longitude": None}]
    enriched, focused = tracker.process_aircraft(raw)
    assert enriched == []
    assert focused is None


def test_process_aircraft_skips_entries_without_callsign():
    tracker = make_tracker()
    raw = [{"icao24": "abc", "callsign": None, "latitude": HOME_LAT, "longitude": HOME_LON}]
    enriched, focused = tracker.process_aircraft(raw)
    assert enriched == []
    assert focused is None


def test_process_aircraft_skips_ignored_callsign_prefixes():
    tracker = make_tracker(ignored_callsign_prefixes=["AIRSIDE", "GND"])
    ground_vehicle = make_aircraft("abc", HOME_LAT, HOME_LON, callsign="AIRSIDE1")
    real_plane = make_aircraft("def", HOME_LAT, HOME_LON, callsign="UAL123")

    enriched, focused = tracker.process_aircraft([ground_vehicle, real_plane])

    assert [a["icao24"] for a in enriched] == ["def"]


def test_process_aircraft_ignored_prefix_match_is_case_insensitive():
    tracker = make_tracker(ignored_callsign_prefixes=["AIRSIDE"])
    raw = [make_aircraft("abc", HOME_LAT, HOME_LON, callsign="airside2")]

    enriched, focused = tracker.process_aircraft(raw)

    assert enriched == []


def test_process_aircraft_computes_distance_and_calls_collaborators():
    alert_engine = Mock(evaluate=Mock(return_value={"level": "rare"}))
    enrichment = Mock(enrich_static=Mock())
    tracker = make_tracker(alert_engine=alert_engine, enrichment=enrichment)

    raw = [make_aircraft("abc", HOME_LAT, HOME_LON)]
    enriched, focused = tracker.process_aircraft(raw)

    assert len(enriched) == 1
    ac = enriched[0]
    assert ac["distance_km"] == 0.0
    assert ac["alert"] == {"level": "rare"}
    enrichment.enrich_static.assert_called_once_with(ac)
    alert_engine.evaluate.assert_called_once_with(ac)


def test_process_aircraft_focuses_nearest_airborne_within_range():
    tracker = make_tracker()
    near = make_aircraft("near", HOME_LAT + 0.01, HOME_LON, callsign="NEAR1")
    far = make_aircraft("far", HOME_LAT + 5, HOME_LON, callsign="FAR1")  # outside focus_km

    enriched, focused = tracker.process_aircraft([far, near])

    assert focused["icao24"] == "near"
    assert focused["focused"] is True


def test_process_aircraft_ignores_ground_aircraft_for_focus():
    tracker = make_tracker()
    grounded = make_aircraft("g1", HOME_LAT, HOME_LON, on_ground=True)

    enriched, focused = tracker.process_aircraft([grounded])

    assert focused is None
    assert "focused" not in enriched[0]


def test_process_aircraft_no_candidates_within_focus_returns_none():
    tracker = make_tracker()
    far = make_aircraft("far", HOME_LAT + 5, HOME_LON)

    _, focused = tracker.process_aircraft([far])

    assert focused is None


def test_build_payload_reflects_current_state():
    tracker = make_tracker()
    tracker.state["aircraft"] = [make_aircraft("abc", HOME_LAT, HOME_LON)]
    tracker.state["focused_icao"] = "abc"

    payload = tracker.build_payload()

    assert payload["home"] == {"lat": HOME_LAT, "lon": HOME_LON}
    assert payload["focus_radius_km"] == FOCUS_KM
    assert payload["focused_icao"] == "abc"
    assert payload["count"] == 1
    assert payload["aircraft"] == tracker.state["aircraft"]
    assert payload["daily_count"] == 0  # nothing recorded via _refresh_once yet


def test_refresh_once_updates_state_and_broadcasts():
    ac = make_aircraft("abc", HOME_LAT, HOME_LON)
    data_source = Mock(fetch_states=AsyncMock(return_value=[ac]))
    manager = Mock(broadcast=AsyncMock())
    enrichment = Mock(enrich_static=Mock(), get_route=AsyncMock(return_value={"origin_iata": "BUD"}))
    tracker = make_tracker(data_source=data_source, manager=manager, enrichment=enrichment)

    asyncio.run(tracker._refresh_once())

    assert len(tracker.state["aircraft"]) == 1
    assert tracker.state["focused_icao"] == "abc"
    assert tracker.state["aircraft"][0]["route"] == {"origin_iata": "BUD"}
    assert tracker.state["updated_at"] is not None
    manager.broadcast.assert_awaited_once()


def test_refresh_once_records_seen_aircraft_in_daily_stats():
    ac = make_aircraft("abc", HOME_LAT, HOME_LON)
    data_source = Mock(fetch_states=AsyncMock(return_value=[ac]))
    enrichment = Mock(enrich_static=Mock(), get_route=AsyncMock(return_value=None))
    tracker = make_tracker(data_source=data_source, enrichment=enrichment)

    asyncio.run(tracker._refresh_once())

    assert tracker.daily_stats.count == 1
    assert tracker.build_payload()["daily_count"] == 1


def test_refresh_once_attaches_times_seen_to_focused_by_registration():
    ac = make_aircraft("abc", HOME_LAT, HOME_LON)
    ac["registration"] = "HA-LVK"
    data_source = Mock(fetch_states=AsyncMock(return_value=[ac]))
    enrichment = Mock(enrich_static=Mock(), get_route=AsyncMock(return_value=None))
    tracker = make_tracker(data_source=data_source, enrichment=enrichment)

    asyncio.run(tracker._refresh_once())
    assert tracker.state["aircraft"][0]["times_seen"] == 1

    # Seen again (e.g. next poll cycle, still today): still counts as 1
    # distinct day so far.
    asyncio.run(tracker._refresh_once())
    assert tracker.state["aircraft"][0]["times_seen"] == 1


def test_refresh_once_no_times_seen_without_registration():
    ac = make_aircraft("abc", HOME_LAT, HOME_LON)
    data_source = Mock(fetch_states=AsyncMock(return_value=[ac]))
    enrichment = Mock(enrich_static=Mock(), get_route=AsyncMock(return_value=None))
    tracker = make_tracker(data_source=data_source, enrichment=enrichment)

    asyncio.run(tracker._refresh_once())

    assert "times_seen" not in tracker.state["aircraft"][0]


def test_refresh_once_does_not_fetch_route_when_nothing_focused():
    far = make_aircraft("far", HOME_LAT + 5, HOME_LON)
    data_source = Mock(fetch_states=AsyncMock(return_value=[far]))
    enrichment = Mock(enrich_static=Mock(), get_route=AsyncMock(return_value=None))
    tracker = make_tracker(data_source=data_source, enrichment=enrichment)

    asyncio.run(tracker._refresh_once())

    assert tracker.state["focused_icao"] is None
    enrichment.get_route.assert_not_awaited()


def test_refresh_once_passes_route_sanity_params_to_get_route():
    ac = make_aircraft("abc", HOME_LAT, HOME_LON)
    ac["baro_altitude"] = 1200
    data_source = Mock(fetch_states=AsyncMock(return_value=[ac]))
    enrichment = Mock(enrich_static=Mock(), get_route=AsyncMock(return_value=None))
    tracker = make_tracker(
        data_source=data_source,
        enrichment=enrichment,
        home_airport_iata="BUD",
        route_sanity_max_altitude_m=3000,
    )

    asyncio.run(tracker._refresh_once())

    enrichment.get_route.assert_awaited_once_with(
        "TEST123", altitude_m=1200, home_iata="BUD", max_altitude_m=3000,
    )


def test_close_sources_closes_primary_and_fallback():
    primary = Mock(close=AsyncMock())
    fallback = Mock(close=AsyncMock())
    tracker = make_tracker(data_source=primary, fallback_source=fallback)

    asyncio.run(tracker.close_sources())

    primary.close.assert_awaited_once()
    fallback.close.assert_awaited_once()


def test_close_sources_without_fallback():
    primary = Mock(close=AsyncMock())
    tracker = make_tracker(data_source=primary, fallback_source=None)

    asyncio.run(tracker.close_sources())

    primary.close.assert_awaited_once()
