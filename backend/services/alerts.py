class AlertEngine:
    def __init__(self, common_types: list[str], emergency_squawks: list[str]):
        self._common = {t.upper() for t in common_types}
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

        if ac_type not in self._common:
            return {
                "level": "rare",
                "reason": f"Rare type: {ac_type}",
                "flash": "gold",
            }
        return None