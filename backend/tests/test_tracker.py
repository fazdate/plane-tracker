"""Unit tests for AircraftTracker's failover/backoff state machine.

This is the highest-risk piece of logic in the tracker (poll_loop delegates
to it) and previously had no test coverage. These tests exercise the sync
helper methods directly rather than the full async poll_loop, since all the
interesting behavior lives in _on_poll_success/_on_poll_failure/_next_sleep_seconds.
"""
from unittest.mock import Mock

import pytest

from tracker import (
    FAILOVER_THRESHOLD,
    MAX_BACKOFF_SECONDS,
    RECOVERY_PROBE_EVERY,
    AircraftTracker,
)

POLL_INTERVAL = 6


def make_tracker(fallback_source=None) -> AircraftTracker:
    primary = Mock(name="primary_source")
    return AircraftTracker(
        data_source=primary,
        poll_interval=POLL_INTERVAL,
        home_lat=0.0,
        home_lon=0.0,
        focus_km=10.0,
        box=Mock(name="box"),
        alert_engine=Mock(name="alert_engine"),
        enrichment=Mock(name="enrichment"),
        manager=Mock(name="manager"),
        fallback_source=fallback_source,
    )


def test_next_sleep_is_poll_interval_when_healthy():
    tracker = make_tracker()
    assert tracker._next_sleep_seconds() == POLL_INTERVAL


def test_backoff_doubles_on_each_failure():
    tracker = make_tracker()  # no fallback, so it just backs off in place
    tracker._on_poll_failure()
    assert tracker._next_sleep_seconds() == POLL_INTERVAL * 1
    tracker._on_poll_failure()
    assert tracker._next_sleep_seconds() == POLL_INTERVAL * 2
    tracker._on_poll_failure()
    assert tracker._next_sleep_seconds() == POLL_INTERVAL * 4


def test_backoff_caps_at_max_backoff_seconds():
    tracker = make_tracker()
    for _ in range(20):
        tracker._on_poll_failure()
    assert tracker._next_sleep_seconds() == MAX_BACKOFF_SECONDS


def test_success_resets_failure_counter_and_backoff():
    tracker = make_tracker()
    tracker._on_poll_failure()
    tracker._on_poll_failure()
    assert tracker._next_sleep_seconds() > POLL_INTERVAL

    tracker._on_poll_success()
    assert tracker._consecutive_failures == 0
    assert tracker._next_sleep_seconds() == POLL_INTERVAL


def test_no_failover_without_fallback_source():
    tracker = make_tracker(fallback_source=None)
    primary = tracker.data_source
    for _ in range(FAILOVER_THRESHOLD + 5):
        tracker._on_poll_failure()
    assert tracker.data_source is primary


def test_failover_switches_to_fallback_after_threshold():
    fallback = Mock(name="fallback_source")
    tracker = make_tracker(fallback_source=fallback)
    primary = tracker.data_source

    for _ in range(FAILOVER_THRESHOLD - 1):
        tracker._on_poll_failure()
    assert tracker.data_source is primary  # not yet switched

    tracker._on_poll_failure()  # threshold-th failure
    assert tracker.data_source is fallback
    assert tracker._consecutive_failures == 0  # reset after switching


def test_stays_on_fallback_until_recovery_probe():
    fallback = Mock(name="fallback_source")
    tracker = make_tracker(fallback_source=fallback)
    primary = tracker.data_source

    for _ in range(FAILOVER_THRESHOLD):
        tracker._on_poll_failure()
    assert tracker.data_source is fallback

    for _ in range(RECOVERY_PROBE_EVERY - 1):
        tracker._on_poll_success()
    assert tracker.data_source is fallback  # still probing

    tracker._on_poll_success()  # recovery-th success
    assert tracker.data_source is primary
    assert tracker._cycles_on_fallback == 0


def test_refailover_after_failed_recovery_probe():
    """If the primary fails again right after being retried, it should fail
    back over to the fallback rather than getting stuck retrying forever."""
    fallback = Mock(name="fallback_source")
    tracker = make_tracker(fallback_source=fallback)

    for _ in range(FAILOVER_THRESHOLD):
        tracker._on_poll_failure()
    assert tracker.data_source is fallback

    for _ in range(RECOVERY_PROBE_EVERY):
        tracker._on_poll_success()
    assert tracker.data_source is tracker._primary_source

    for _ in range(FAILOVER_THRESHOLD):
        tracker._on_poll_failure()
    assert tracker.data_source is fallback
