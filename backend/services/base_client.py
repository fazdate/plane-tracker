"""Abstract base for aircraft data sources.

All clients must return a list of normalized aircraft dicts with these keys:
  icao24, callsign, origin_country, longitude, latitude,
  baro_altitude (meters), on_ground (bool), velocity (m/s),
  true_track (deg), vertical_rate (m/s), squawk,
  aircraft_type (optional), registration (optional)
"""
from abc import ABC, abstractmethod

from services.geo import BoundingBox


class AircraftDataSource(ABC):
    @abstractmethod
    async def fetch_states(self, box: BoundingBox) -> list[dict]:
        """Return normalized aircraft dicts within the bounding box."""
        ...

    @abstractmethod
    async def close(self) -> None:
        ...