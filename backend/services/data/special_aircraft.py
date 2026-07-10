"""Non-airline aircraft (military, government, police, medical, etc.) whose
callsigns don't follow the standard 3-letter ICAO airline codes handled by
airlines.py.

Unlike airlines.py, these aren't hardcoded here - they're supplied by the
user via config.yaml's `special_aircraft` section (see config.py), so adding
support for e.g. a new police/EMS helicopter callsign needs no code changes:
just a callsign prefix, a display name, and optionally a logo/picture URL
and whether it's a helicopter. This module only implements the matching.
"""


class SpecialAircraftMatcher:
    """Matches a callsign against user-configured special-aircraft prefixes.

    Prefixes are matched case-insensitively and checked longest-first, so a
    more specific prefix (e.g. "MEDIC") always wins over a shorter, more
    general one that would also match (e.g. "M"). Aircraft whose callsign
    already matches a known airline (see airlines.py) should be checked
    against that first - this is only meant as a fallback for callsigns
    airlines.py doesn't recognize.
    """

    def __init__(self, entries: list[dict] | None = None):
        self._entries = sorted(
            (self._normalize(e) for e in (entries or [])),
            key=lambda e: len(e["prefix"]),
            reverse=True,
        )

    @staticmethod
    def _normalize(entry: dict) -> dict:
        return {
            "prefix": str(entry["prefix"]).strip().upper(),
            "name": entry["name"],
            "logo_url": (entry.get("logo_url") or "").strip() or None,
            "is_helicopter": bool(entry.get("is_helicopter", False)),
        }

    def match(self, callsign: str | None) -> dict | None:
        """Return the matching entry (dict with name/logo_url/is_helicopter),
        or None if no configured prefix matches."""
        if not callsign:
            return None
        callsign = callsign.strip().upper()
        for entry in self._entries:
            if entry["prefix"] and callsign.startswith(entry["prefix"]):
                return entry
        return None
