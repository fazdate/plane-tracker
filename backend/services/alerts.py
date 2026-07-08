class AlertEngine:
    def __init__(self, boring_types: list[str], emergency_squawks: list[str]):
        self._boring = {t.upper() for t in boring_types}
        self._emergency = set(emergency_squawks)

    def evaluate(self, aircraft: dict) -> dict | None:
        squawk = aircraft.get("squawk")
        if squawk in self._emergency:
            return {
                "level": "emergency",
                "reason": f"Emergency squawk {squawk}",
                "flash": "red",
            }

        ac_type = (aircraft.get("aircraft_type") or "").upper()
        if not ac_type:
            return None  # unknown type -> don't alert (avoid noise)

        if ac_type not in self._boring:
            return {
                "level": "interesting",
                "reason": f"Uncommon type: {ac_type}",
                "flash": "gold",
            }
        return None