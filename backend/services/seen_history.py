"""Tracks how many distinct days each aircraft (by registration) has been seen.

Backed by the same style of SQLite table as DailyStats: one row per
(day, registration) pair, so repeated sightings within a single poll cycle
(or across many poll cycles the same day) only count once per day, and the
history survives an app restart partway through the day.
"""
import sqlite3
from datetime import date
from typing import Iterable, Optional

DEFAULT_DB_PATH = "daily_stats.db"


class SeenHistory:
    """Counts the number of distinct days a registration has been seen."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        # check_same_thread=False: see DailyStats for rationale (same
        # single-shared-connection access pattern from the poll loop).
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS aircraft_sightings ("
            "day TEXT NOT NULL, registration TEXT NOT NULL, "
            "PRIMARY KEY (day, registration))"
        )
        self._conn.commit()

    def record(self, registrations: Iterable[Optional[str]]) -> None:
        """Record the registrations seen in the current poll cycle. Falsy
        values (missing registration) are ignored."""
        today = date.today().isoformat()
        rows = [(today, reg) for reg in registrations if reg]
        if not rows:
            return
        self._conn.executemany(
            "INSERT OR IGNORE INTO aircraft_sightings (day, registration) VALUES (?, ?)",
            rows,
        )
        self._conn.commit()

    def count(self, registration: str) -> int:
        """Number of distinct days this registration has been seen (including today)."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM aircraft_sightings WHERE registration = ?",
            (registration,),
        ).fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self._conn.close()
