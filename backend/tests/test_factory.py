"""Unit tests for the data-source factory."""
from types import SimpleNamespace

import pytest

from services.adsb_client import AdsbLolClient
from services.factory import create_data_source
from services.opensky_client import OpenSkyClient


def make_config(provider: str) -> SimpleNamespace:
    return SimpleNamespace(
        home_lat=47.5,
        home_lon=19.1,
        raw={
            "data_source": {"provider": provider},
            "opensky": {"poll_interval_seconds": 5},
            "adsblol": {"poll_interval_seconds": 6},
        },
    )


def test_adsblol_provider_without_opensky_credentials(monkeypatch):
    monkeypatch.delenv("OPENSKY_CLIENT_ID", raising=False)
    monkeypatch.delenv("OPENSKY_CLIENT_SECRET", raising=False)

    client, fallback, interval = create_data_source(make_config("adsblol"))

    assert isinstance(client, AdsbLolClient)
    assert fallback is None
    assert interval == 6


def test_adsblol_provider_with_opensky_credentials_gets_fallback(monkeypatch):
    monkeypatch.setenv("OPENSKY_CLIENT_ID", "id")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "secret")

    client, fallback, interval = create_data_source(make_config("adsblol"))

    assert isinstance(client, AdsbLolClient)
    assert isinstance(fallback, OpenSkyClient)
    assert interval == 6


def test_opensky_provider_requires_credentials(monkeypatch):
    monkeypatch.setenv("OPENSKY_CLIENT_ID", "id")
    monkeypatch.setenv("OPENSKY_CLIENT_SECRET", "secret")

    client, fallback, interval = create_data_source(make_config("opensky"))

    assert isinstance(client, OpenSkyClient)
    assert isinstance(fallback, AdsbLolClient)
    assert interval == 5


def test_provider_is_case_insensitive(monkeypatch):
    monkeypatch.delenv("OPENSKY_CLIENT_ID", raising=False)
    monkeypatch.delenv("OPENSKY_CLIENT_SECRET", raising=False)
    config = make_config("ADSBLOL")

    client, _, _ = create_data_source(config)

    assert isinstance(client, AdsbLolClient)


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown data_source.provider"):
        create_data_source(make_config("bogus"))
