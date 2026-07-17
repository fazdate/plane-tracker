"""ICAO aircraft type code -> friendly name. Common types.
Full list: https://www.icao.int/publications/DOC8643/Pages/Search.aspx
"""

AIRCRAFT_TYPES: dict[str, str] = {
    # Airbus
    "A319": "Airbus A319", "A320": "Airbus A320", "A321": "Airbus A321",
    "A20N": "Airbus A320neo", "A21N": "Airbus A321neo",
    "A318": "Airbus A318",
    "A332": "Airbus A330-200", "A333": "Airbus A330-300",
    "A339": "Airbus A330-900neo",
    "A342": "Airbus A340-200", "A343": "Airbus A340-300",
    "A345": "Airbus A340-500", "A346": "Airbus A340-600",
    "A359": "Airbus A350-900", "A35K": "Airbus A350-1000",
    "A388": "Airbus A380-800",
    "BCS1": "Airbus A220-100", "BCS3": "Airbus A220-300",
    "A310": "Airbus A310",
    # Boeing
    "B737": "Boeing 737", "B733": "Boeing 737-300",
    "B734": "Boeing 737-400", "B735": "Boeing 737-500",
    "B738": "Boeing 737-800",
    "B739": "Boeing 737-900", "B38M": "Boeing 737 MAX 8",
    "B39M": "Boeing 737 MAX 9", "B752": "Boeing 757-200",
    "B762": "Boeing 767-200",
    "B763": "Boeing 767-300", "B764": "Boeing 767-400",
    "B772": "Boeing 777-200", "B77L": "Boeing 777-200LR",
    "B773": "Boeing 777-300", "B77W": "Boeing 777-300ER",
    "B77F": "Boeing 777F",
    "B788": "Boeing 787-8", "B789": "Boeing 787-9", "B78X": "Boeing 787-10",
    "B744": "Boeing 747-400", "B748": "Boeing 747-8",
    "B462": "BAe 146", "B463": "BAe 146-300",
    # Embraer
    "E170": "Embraer E170", "E175": "Embraer E175",
    "E190": "Embraer E190", "E195": "Embraer E195",
    "E290": "Embraer E190-E2", "E295": "Embraer E195-E2",
    # Regional / turboprop
    "AT72": "ATR 72", "AT76": "ATR 72-600", "AT75": "ATR 72-500",
    "AT45": "ATR 42-500",
    "DH8D": "Bombardier Dash 8 Q400",
    "CRJ2": "Bombardier CRJ200", "CRJ7": "Bombardier CRJ700",
    "CRJ9": "Bombardier CRJ900",
    "SF34": "Saab 340", "SB20": "Saab 2000",
    "D328": "Dornier 328", "L410": "Let L-410 Turbolet",
    # Bizjets / GA
    "C172": "Cessna 172", "C152": "Cessna 152", "C182": "Cessna 182",
    "PA28": "Piper PA-28 Cherokee", "PA34": "Piper PA-34 Seneca",
    "SR20": "Cirrus SR20", "SR22": "Cirrus SR22",
    "C25A": "Cessna Citation CJ2", "C56X": "Cessna Citation Excel",
    "GLF6": "Gulfstream G650", "GLF5": "Gulfstream G550",
    "GLF4": "Gulfstream G450",
    "CL60": "Bombardier Challenger 600", "CL30": "Bombardier Challenger 300",
    "GLEX": "Bombardier Global Express",
    "F900": "Dassault Falcon 900", "F2TH": "Dassault Falcon 2000",
    "LJ45": "Learjet 45", "E55P": "Embraer Phenom 300",
    "B350": "Beechcraft King Air 350",
    "PC12": "Pilatus PC-12",
    # Cargo / special
    "A124": "Antonov An-124", "AN12": "Antonov An-12",
    "AN26": "Antonov An-26",
    "IL76": "Ilyushin Il-76", "MD11": "McDonnell Douglas MD-11",
    # Military / overflight
    "C130": "Lockheed C-130 Hercules", "C17": "Boeing C-17 Globemaster III",
    "A400": "Airbus A400M Atlas",
    # Helicopters
    "EC35": "Airbus H135", "EC45": "Airbus H145",
    "EC30": "Airbus H130", "EC55": "Airbus H155",
    "AS50": "Airbus H125 (AS350 Ecureuil)",
    "A139": "AgustaWestland AW139", "A109": "AgustaWestland AW109",
    "B06": "Bell 206 JetRanger", "B407": "Bell 407", "B429": "Bell 429",
    "S76": "Sikorsky S-76", "S92": "Sikorsky S-92",
    "H500": "MD Helicopters MD 500",
    "R44": "Robinson R44", "R22": "Robinson R22",
    "MI8": "Mil Mi-8", "MI17": "Mil Mi-17",
    "H47": "Boeing CH-47 Chinook", "H60": "Sikorsky UH-60 Black Hawk",
    "EC25": "Airbus H225M Caracal",
}

# ICAO type designators that are helicopters (the "Helicopters" entries
# above), used to pick a helicopter icon on the map instead of the default
# fixed-wing plane icon. See also special_aircraft.py, which lets a
# callsign-based match force this on when the aircraft's reported type is
# missing or unrecognized (e.g. some military/EMS helicopters).
HELICOPTER_TYPES: frozenset[str] = frozenset({
    "EC35", "EC45", "EC30", "EC55", "AS50", "A139", "A109",
    "B06", "B407", "B429", "S76", "S92", "H500", "R44", "R22",
    "MI8", "MI17", "H47", "H60", "EC25",
})


def aircraft_type_name(type_code: str | None) -> str | None:
    if not type_code:
        return None
    return AIRCRAFT_TYPES.get(type_code.upper(), type_code)  # fallback: raw code


def is_helicopter_type(type_code: str | None) -> bool:
    return bool(type_code) and type_code.upper() in HELICOPTER_TYPES