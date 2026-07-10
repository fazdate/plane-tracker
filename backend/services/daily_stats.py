"""Tracks the number of distinct aircraft seen since local midnight.

Backed by a small SQLite database (rather than an in-memory set) so the count
survives an app restart partway through the day; rows from previous days are
purged whenever the calendar day rolls over.
"""
import sqlite3
from datetime import date
from typing import Iterable

DEFAULT_DB_PATH = "daily_stats.db"


class DailyStats:
    """Counts distinct aircraft (by icao24) seen since local midnight."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._day = date.today()
        # check_same_thread=False: the tracker's poll loop and any request
        # handler reading `count` may run on different asyncio-scheduled
        # threads/tasks, but calls are never truly concurrent (no threads of
        # our own), so a single shared connection is safe here.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS daily_aircraft ("
            "day TEXT NOT NULL, icao24 TEXT NOT NULL, "
            "PRIMARY KEY (day, icao24))"
        )
        self._conn.commit()
        self._purge_old_days()

    def record(self, icao24_values: Iterable[str]) -> None:
        """Record the icao24 codes seen in the current poll cycle."""
        self._roll_if_new_day()
        rows = [(self._day.isoformat(), icao) for icao in icao24_values]
        if not rows:
            return
        self._conn.executemany(
            "INSERT OR IGNORE INTO daily_aircraft (day, icao24) VALUES (?, ?)", rows
        )
        self._conn.commit()

    @property
    def count(self) -> int:
        self._roll_if_new_day()
        row = self._conn.execute(
            "SELECT COUNT(*) FROM daily_aircraft WHERE day = ?", (self._day.isoformat(),)
        ).fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self._conn.close()

    def _roll_if_new_day(self) -> None:
        today = date.today()
        if today != self._day:
            self._day = today
            self._purge_old_days()

    def _purge_old_days(self) -> None:
        """Drop rows for any day other than the current one, both on init
        (cleaning up after previous days) and on rollover."""
        self._conn.execute(
            "DELETE FROM daily_aircraft WHERE day != ?", (self._day.isoformat(),)
        )
        self._conn.commit()
