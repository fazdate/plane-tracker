"""Geographic calculations: distances and bounding boxes."""
import math
from dataclasses import dataclass


@dataclass
class BoundingBox:
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometers."""
    r = 6371.0  # Earth radius km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(a))


def bounding_box(lat: float, lon: float, radius_km: float) -> BoundingBox:
    """Approximate bounding box around a point for a given radius."""
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * math.cos(math.radians(lat)))
    return BoundingBox(
        lat_min=lat - lat_delta,
        lat_max=lat + lat_delta,
        lon_min=lon - lon_delta,
        lon_max=lon + lon_delta,
    )