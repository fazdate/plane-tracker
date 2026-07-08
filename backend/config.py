"""Application configuration: environment variables and YAML settings."""
import os

import yaml
from dotenv import load_dotenv

from services.geo import BoundingBox, bounding_box

# Top-level sections and keys that must be present in config.yaml.
_REQUIRED_KEYS = {
    "data_source": ["provider"],
    "zones": ["bounding_box_km", "focus_radius_km"],
    "alerts": ["boring_types", "emergency_squawks"],
}
# Home coordinates live in the environment (not config.yaml) so they're never
# committed to version control.
_REQUIRED_ENV = ["HOME_LATITUDE", "HOME_LONGITUDE"]
_VALID_PROVIDERS = ("adsblol", "opensky")


class ConfigError(Exception):
    """Raised when config.yaml is missing required keys or is malformed."""


class Config:
    """Loads .env and config.yaml, exposing both derived and raw settings."""

    def __init__(self, path: str = "config.yaml"):
        load_dotenv()
        with open(path) as f:
            self.raw: dict = yaml.safe_load(f) or {}

        self._validate()

        self.home_lat: float = self._env_float("HOME_LATITUDE")
        self.home_lon: float = self._env_float("HOME_LONGITUDE")
        self.bbox_km: float = self.raw["zones"]["bounding_box_km"]
        self.focus_km: float = self.raw["zones"]["focus_radius_km"]
        self.box: BoundingBox = bounding_box(self.home_lat, self.home_lon, self.bbox_km)

    def _validate(self) -> None:
        """Check required sections/keys up front so startup fails with a
        clear message instead of a raw KeyError deep in some other module."""
        errors = []
        for section, keys in _REQUIRED_KEYS.items():
            if section not in self.raw:
                errors.append(f"missing section '{section}'")
                continue
            for key in keys:
                if key not in self.raw[section]:
                    errors.append(f"missing '{section}.{key}'")

        provider = (self.raw.get("data_source") or {}).get("provider")
        if provider is not None:
            provider = str(provider).lower()
            if provider not in _VALID_PROVIDERS:
                errors.append(
                    f"data_source.provider must be one of {_VALID_PROVIDERS}, got '{provider}'"
                )
            elif provider not in self.raw:
                errors.append(f"missing section '{provider}' (poll_interval_seconds)")
            elif "poll_interval_seconds" not in self.raw[provider]:
                errors.append(f"missing '{provider}.poll_interval_seconds'")

        for name in _REQUIRED_ENV:
            if name not in os.environ:
                errors.append(f"missing environment variable '{name}'")

        if errors:
            raise ConfigError("Invalid configuration:\n  - " + "\n  - ".join(errors))

    @staticmethod
    def env(name: str) -> str:
        """Fetch a required environment variable."""
        try:
            return os.environ[name]
        except KeyError:
            raise ConfigError(f"Missing required environment variable: {name}") from None

    @classmethod
    def _env_float(cls, name: str) -> float:
        """Fetch a required environment variable and parse it as a float."""
        value = cls.env(name)
        try:
            return float(value)
        except ValueError:
            raise ConfigError(
                f"Environment variable {name} must be a number, got '{value}'"
            ) from None
