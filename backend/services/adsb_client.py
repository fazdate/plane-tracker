"""adsb.lol data source. Free, no auth, radius-based query.

API: https://api.adsb.lol/v2/lat/{lat}/lon/{lon}/dist/{nm}
Docs: https://api.adsb.lol/docs
"""
import logging
import math

import httpx

from services.base_client import AircraftDataSource
from services.geo import BoundingBox

logger = logging.getLogger(__name__)

BASE_URL = "https://api.adsb.lol/v2"


class AdsbLolClient(AircraftDataSource):
    def __init__(self, center_lat: float, center_lon: float):
        self._lat = center_lat
        self._lon = center_lon
        self._http = httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "plane-tracker-hobby/1.0"},
        )

    async def fetch_states(self, box: BoundingBox) -> list[dict]:
        """Fetch by radius derived from bounding box, then filter to box."""
        radius_nm = self._box_to_radius_nm(box)
        url = f"{BASE_URL}/lat/{self._lat}/lon/{self._lon}/dist/{radius_nm}"
        resp = await self._http.get(url)
        resp.raise_for_status()
        payload = resp.json()
        raw = payload.get("ac") or []

        results = []
        for a in raw:
            norm = self._normalize(a)
            if norm is None:
                continue
            # Keep only those inside the configured bounding box
            lat, lon = norm["latitude"], norm["longitude"]
            if lat is None or lon is None:
                continue
            if not (box.lat_min <= lat <= box.lat_max
                    and box.lon_min <= lon <= box.lon_max):
                continue
            results.append(norm)
        return results

    def _box_to_radius_nm(self, box: BoundingBox) -> int:
        """Radius (nautical miles) large enough to cover the box corners."""
        # Half-diagonal of the box in km
        lat_span_km = (box.lat_max - box.lat_min) * 111.0 / 2
        lon_span_km = (box.lon_max - box.lon_min) * \
            (111.0 * math.cos(math.radians(self._lat))) / 2
        half_diag_km = math.hypot(lat_span_km, lon_span_km)
        radius_nm = half_diag_km / 1.852
        return max(1, math.ceil(radius_nm))

    @staticmethod
    def _normalize(a: dict) -> dict | None:
        """Map adsb.lol fields to our normalized schema."""
        lat = a.get("lat")
        lon = a.get("lon")
        if lat is None or lon is None:
            return None

        # Altitude: "alt_baro" can be int (feet) or "ground"
        alt_baro = a.get("alt_baro")
        on_ground = (alt_baro == "ground")
        alt_m = None
        if isinstance(alt_baro, (int, float)):
            alt_m = alt_baro * 0.3048  # feet -> meters

        # Ground speed: knots -> m/s
        gs = a.get("gs")
        velocity = gs * 0.514444 if isinstance(gs, (int, float)) else None

        # Vertical rate: feet/min -> m/s
        vr = a.get("baro_rate")
        vertical_rate = vr * 0.00508 if isinstance(vr, (int, float)) else None

        callsign = a.get("flight")
        if callsign:
            callsign = callsign.strip()

        return {
            "icao24": (a.get("hex") or "").lower(),
            "callsign": callsign,
            "origin_country": None,          # adsb.lol doesn't provide directly
            "longitude": lon,
            "latitude": lat,
            "baro_altitude": alt_m,
            "on_ground": on_ground,
            "velocity": velocity,
            "true_track": a.get("track"),
            "vertical_rate": vertical_rate,
            "squawk": a.get("squawk"),
            # Bonus enrichment adsb.lol gives us for free:
            "aircraft_type": a.get("t"),       # e.g. "B738", "C172"
            "registration": a.get("r"),        # e.g. "HA-LVK"
        }

    async def close(self) -> None:
        await self._http.aclose()