"""Unit tests for Config loading/validation."""
import pytest

from config import Config, ConfigError

VALID_YAML = """
data_source:
  provider: adsblol

zones:
  bounding_box_km: 30
  focus_radius_km: 10

adsblol:
  poll_interval_seconds: 6

alerts:
  common_types:
    - B738
  emergency_squawks:
    - "7700"
"""


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch):
    """Config.__init__ calls load_dotenv(), which would otherwise pick up the
    real backend/.env file (including real HOME_LATITUDE/HOME_LONGITUDE) and
    make these tests depend on environment/machine state. Neutralize it and
    give each test a clean, explicit slate for the home-location env vars."""
    monkeypatch.setattr("config.load_dotenv", lambda: None)
    monkeypatch.delenv("HOME_LATITUDE", raising=False)
    monkeypatch.delenv("HOME_LONGITUDE", raising=False)


def write_yaml(tmp_path, content: str) -> str:
    path = tmp_path / "config.yaml"
    path.write_text(content)
    return str(path)


def test_valid_config_loads_derived_fields(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")

    config = Config(write_yaml(tmp_path, VALID_YAML))

    assert config.home_lat == 47.5
    assert config.home_lon == 19.1
    assert config.bbox_km == 30
    assert config.focus_km == 10
    assert config.box.lat_min < config.home_lat < config.box.lat_max


def test_home_airport_iata_and_route_sanity_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    monkeypatch.delenv("HOME_AIRPORT_IATA", raising=False)

    config = Config(write_yaml(tmp_path, VALID_YAML))

    assert config.home_airport_iata is None
    assert config.route_sanity_max_altitude_m == 3000


def test_home_airport_iata_is_normalized_and_route_sanity_is_overridable(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    monkeypatch.setenv("HOME_AIRPORT_IATA", " bud ")
    content = VALID_YAML + "\nroute_sanity:\n  max_altitude_m: 1500\n"

    config = Config(write_yaml(tmp_path, content))

    assert config.home_airport_iata == "BUD"
    assert config.route_sanity_max_altitude_m == 1500


def test_ignored_callsign_prefixes_defaults_to_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")

    config = Config(write_yaml(tmp_path, VALID_YAML))

    assert config.ignored_callsign_prefixes == []


def test_ignored_callsign_prefixes_are_loaded_and_normalized(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    content = VALID_YAML + "\nfilters:\n  ignored_callsign_prefixes:\n    - airside\n    - ' Gnd '\n"

    config = Config(write_yaml(tmp_path, content))

    assert config.ignored_callsign_prefixes == ["AIRSIDE", "GND"]


def test_daily_stats_db_path_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")

    config = Config(write_yaml(tmp_path, VALID_YAML))

    assert config.daily_stats_db_path == "daily_stats.db"


def test_daily_stats_db_path_is_overridable(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    content = VALID_YAML + "\ndaily_stats:\n  db_path: /var/lib/plane-tracker/stats.db\n"

    config = Config(write_yaml(tmp_path, content))

    assert config.daily_stats_db_path == "/var/lib/plane-tracker/stats.db"


def test_special_aircraft_defaults_to_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")

    config = Config(write_yaml(tmp_path, VALID_YAML))

    assert config.special_aircraft == []


def test_special_aircraft_is_loaded(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    content = VALID_YAML + (
        "\nspecial_aircraft:\n"
        "  - prefix: MEDIC\n"
        "    name: OMSZ Helicopter\n"
        "    is_helicopter: true\n"
    )

    config = Config(write_yaml(tmp_path, content))

    assert config.special_aircraft == [
        {"prefix": "MEDIC", "name": "OMSZ Helicopter", "is_helicopter": True}
    ]


def test_special_aircraft_entry_missing_prefix_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    content = VALID_YAML + "\nspecial_aircraft:\n  - name: OMSZ Helicopter\n"

    with pytest.raises(ConfigError, match=r"special_aircraft\[0\] must have a 'prefix' and a 'name'"):
        Config(write_yaml(tmp_path, content))


def test_special_aircraft_entry_missing_name_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    content = VALID_YAML + "\nspecial_aircraft:\n  - prefix: MEDIC\n"

    with pytest.raises(ConfigError, match=r"special_aircraft\[0\] must have a 'prefix' and a 'name'"):
        Config(write_yaml(tmp_path, content))


def test_missing_top_level_section_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    content = VALID_YAML.replace("zones:\n  bounding_box_km: 30\n  focus_radius_km: 10\n", "")

    with pytest.raises(ConfigError, match="missing section 'zones'"):
        Config(write_yaml(tmp_path, content))


def test_missing_key_within_section_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    content = VALID_YAML.replace("  focus_radius_km: 10\n", "")

    with pytest.raises(ConfigError, match="missing 'zones.focus_radius_km'"):
        Config(write_yaml(tmp_path, content))


def test_invalid_provider_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    content = VALID_YAML.replace("provider: adsblol", "provider: bogus")

    with pytest.raises(ConfigError, match="data_source.provider must be one of"):
        Config(write_yaml(tmp_path, content))


def test_provider_missing_poll_interval_section_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    content = VALID_YAML.replace(
        "adsblol:\n  poll_interval_seconds: 6\n", ""
    )

    with pytest.raises(ConfigError, match="missing section 'adsblol'"):
        Config(write_yaml(tmp_path, content))


def test_provider_missing_poll_interval_key_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")
    content = VALID_YAML.replace(
        "  poll_interval_seconds: 6\n", "  other_key: 1\n"
    )

    with pytest.raises(ConfigError, match="missing 'adsblol.poll_interval_seconds'"):
        Config(write_yaml(tmp_path, content))


def test_missing_home_latitude_env_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")  # latitude left unset

    with pytest.raises(ConfigError, match="missing environment variable 'HOME_LATITUDE'"):
        Config(write_yaml(tmp_path, VALID_YAML))


def test_missing_home_longitude_env_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "47.5")  # longitude left unset

    with pytest.raises(ConfigError, match="missing environment variable 'HOME_LONGITUDE'"):
        Config(write_yaml(tmp_path, VALID_YAML))


def test_non_numeric_home_latitude_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME_LATITUDE", "not-a-number")
    monkeypatch.setenv("HOME_LONGITUDE", "19.1")

    with pytest.raises(ConfigError, match="HOME_LATITUDE must be a number"):
        Config(write_yaml(tmp_path, VALID_YAML))


def test_env_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("PLANE_TRACKER_TEST_VAR", "hello")
    assert Config.env("PLANE_TRACKER_TEST_VAR") == "hello"


def test_env_raises_when_missing(monkeypatch):
    monkeypatch.delenv("PLANE_TRACKER_TEST_VAR_MISSING", raising=False)
    with pytest.raises(ConfigError, match="PLANE_TRACKER_TEST_VAR_MISSING"):
        Config.env("PLANE_TRACKER_TEST_VAR_MISSING")
