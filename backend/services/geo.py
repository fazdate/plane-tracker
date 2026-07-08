"""Geographic calculations: distances, bounding boxes, and sun position."""
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


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


# --- Sunrise/sunset (NOAA "sunrise equation" approximation) ---
# Accurate to within a couple of minutes for most latitudes, which is plenty
# for a cosmetic day/night theme switch -- no external API/key needed.
# Reference: https://en.wikipedia.org/wiki/Sunrise_equation
_JULIAN_UNIX_EPOCH = 2440587.5  # Julian date of 1970-01-01T00:00:00Z


def _julian_day(d: date) -> float:
    return d.toordinal() + 1721424.5  # proleptic-Gregorian ordinal -> Julian day


def _julian_to_utc_datetime(jd: float) -> datetime:
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(days=jd - _JULIAN_UNIX_EPOCH)


def sun_times(lat: float, lon: float, on_date: date) -> tuple[datetime, datetime] | None:
    """Return (sunrise_utc, sunset_utc) for the given date and location, or
    None if the sun doesn't rise/set that day (polar day/night). `lon` uses
    the standard convention where East is positive."""
    lw = -lon  # the reference algorithm measures longitude positive-West
    j_date = _julian_day(on_date)
    # Nearest solar-noon-aligned day count since J2000, adjusted for longitude.
    n = round(j_date - 2451545.0009 - lw / 360.0)
    # Days since J2000 (small, relative value -- NOT an absolute Julian date)
    # used for the mean anomaly; solar_transit below needs the absolute one.
    j_rel = n + lw / 360.0 + 0.0009

    solar_mean_anomaly_deg = (357.5291 + 0.98560028 * j_rel) % 360
    solar_mean_anomaly = math.radians(solar_mean_anomaly_deg)
    center = (
        1.9148 * math.sin(solar_mean_anomaly)
        + 0.0200 * math.sin(2 * solar_mean_anomaly)
        + 0.0003 * math.sin(3 * solar_mean_anomaly)
    )
    ecliptic_long = math.radians((solar_mean_anomaly_deg + center + 180.0 + 102.9372) % 360)
    solar_transit = (
        2451545.0009 + lw / 360.0 + n
        + 0.0053 * math.sin(solar_mean_anomaly)
        - 0.0069 * math.sin(2 * ecliptic_long)
    )
    sin_declination = math.sin(ecliptic_long) * math.sin(math.radians(23.4397))
    declination = math.asin(sin_declination)

    lat_rad = math.radians(lat)
    cos_hour_angle = (
        math.sin(math.radians(-0.833)) - math.sin(lat_rad) * sin_declination
    ) / (math.cos(lat_rad) * math.cos(declination))
    if cos_hour_angle > 1:
        return None  # polar night: sun never rises
    if cos_hour_angle < -1:
        return None  # polar day: sun never sets

    hour_angle_deg = math.degrees(math.acos(cos_hour_angle))
    sunrise = _julian_to_utc_datetime(solar_transit - hour_angle_deg / 360.0)
    sunset = _julian_to_utc_datetime(solar_transit + hour_angle_deg / 360.0)
    return sunrise, sunset


def is_daytime(lat: float, lon: float, when: datetime | None = None) -> bool:
    """Whether the sun is currently above the horizon at the given location.

    Defaults to "day" for polar day/night edge cases and when `when` isn't
    given (uses the current time); this is only used for a cosmetic theme
    switch, not anything safety-critical."""
    when = when.astimezone(timezone.utc) if when else datetime.now(timezone.utc)
    times = sun_times(lat, lon, when.date())
    if times is None:
        return True
    sunrise, sunset = times
    return sunrise <= when <= sunset