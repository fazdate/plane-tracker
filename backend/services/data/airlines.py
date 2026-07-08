"""ICAO airline code -> (friendly name, IATA code). Common carriers at/near BUD.
Extend freely. Full list: https://en.wikipedia.org/wiki/List_of_airline_codes

The IATA code is used to fetch the airline's logo (see enrichment.py).
Use None when an airline has no IATA code (e.g. rare carriers).
"""

AIRLINES: dict[str, tuple[str, str | None]] = {
    # Hungary / nearby & frequent BUD traffic
    "WZZ": ("Wizz Air", "W6"),
    "WMT": ("Wizz Air Malta", "W9"),
    "WUK": ("Wizz Air UK", "W4"),
    "WAZ": ("Wizz Air Abu Dhabi", "5W"),
    "RYR": ("Ryanair", "FR"),
    "RYS": ("Ryanair Sun", "FR"),
    "RUK": ("Ryanair UK", "RK"),
    "BZZ": ("Buzz", "FR"),
    "EJU": ("easyJet Europe", "EC"),
    "EZY": ("easyJet", "U2"),
    "EZS": ("easyJet Switzerland", "EZS"),
    # DACH region
    "DLH": ("Lufthansa", "LH"),
    "GEC": ("Lufthansa Cargo", "GEC"),
    "CLH": ("Lufthansa CityLine", "CL"),
    "AUA": ("Austrian Airlines", "OS"),
    "SWR": ("Swiss", "LX"),
    "GWI": ("Eurowings", "EW"),
    "EWG": ("Eurowings", "EW"),
    "CFG": ("Condor", "DE"),
    "OAW": ("Helvetic Airways", "2L"),
    "EDW": ("Edelweiss Air", "WK"),
    # Benelux
    "KLM": ("KLM", "KL"),
    "KLC": ("KLM Cityhopper", "WA"),
    "TRA": ("Transavia", "HV"),
    "TFL": ("Transavia France", "TO"),
    "BEL": ("Brussels Airlines", "SN"),
    "LGL": ("Luxair", "LG"),
    # France
    "AFR": ("Air France", "AF"),
    "FGL": ("French Bee", "BF"),
    "XLF": ("Corsair", "SS"),
    "HOP": ("HOP!", "A5"),
    # UK / Ireland
    "BAW": ("British Airways", "BA"),
    "SHT": ("British Airways (Shuttle)", "BA"),
    "VIR": ("Virgin Atlantic", "VS"),
    "EIN": ("Aer Lingus", "EI"),
    "EXS": ("Jet2", "LS"),
    "TOM": ("TUI Airways", "BY"),
    # Turkey / Middle East
    "THY": ("Turkish Airlines", "TK"),
    "TQC": ("AnadoluJet", "TK"),
    "PGT": ("Pegasus", "PC"),
    "SXS": ("SunExpress", "XQ"),
    "CAI": ("Corendon Airlines", "XC"),
    "QTR": ("Qatar Airways", "QR"),
    "UAE": ("Emirates", "EK"),
    "ETD": ("Etihad Airways", "EY"),
    "MSR": ("EgyptAir", "MS"),
    "RJA": ("Royal Jordanian", "RJ"),
    "MEA": ("Middle East Airlines", "ME"),
    "SVA": ("Saudia", "SV"),
    "GFA": ("Gulf Air", "GF"),
    "KAC": ("Kuwait Airways", "KU"),
    "ELY": ("El Al", "LY"),
    "ISR": ("Israir", "6H"),
    "ABY": ("Air Arabia", "G9"),
    "FDB": ("flydubai", "FZ"),
    "MGH": ("Air Anka", "6K"),
    "NIA": ("Sky Vision Airlines", "SE"),
    "KNE": ("Flynas", "XY"),
    # Africa
    "ETH": ("Ethiopian Airlines", "ET"),
    "SAA": ("South African Airways", "SA"),
    "RAM": ("Royal Air Maroc", "AT"),
    "TAR": ("Tunisair", "TU"),
    "MSC": ("Air Cairo", "SM"),
    "KQA": ("Kenya Airways", "KQ"),
    "DAH": ("Air Algérie", "AH"),
    # Central / Eastern Europe
    "LOT": ("LOT Polish Airlines", "LO"),
    "CTN": ("Croatia Airlines", "OU"),
    "ROT": ("TAROM", "RO"),
    "CSA": ("Czech Airlines (CSA)", "OK"),
    "TVS": ("Smartwings", "QS"),
    "ASL": ("Air Serbia", "JU"),
    "BTI": ("airBaltic", "BT"),
    "ENT": ("Enter Air", "E4"),
    "UZB": ("Uzbekistan Airways", "HY"),
    "AZQ": ("Silk Avia", "US"),
    "AUI": ("Ukraine International Airlines", "PS"),
    "BEK": ("Buta Airways", "J2"),
    "UTN": ("Skyline Express", "QU"),
    "TGZ": ("Georgian Airways", "A9"),
    # Southern Europe
    "IBE": ("Iberia", "IB"),
    "VLG": ("Vueling", "VY"),
    "VOE": ("Volotea", "V7"),
    "ANE": ("Air Nostrum", "YW"),
    "AEA": ("Air Europa", "UX"),
    "TAP": ("TAP Air Portugal", "TP"),
    "AZA": ("ITA Airways", "AZ"),
    "AZI": ("Azul Linhas Aereas (ITA regional tag, rare)", "AD"),
    "NOS": ("Neos", "NO"),
    "AEE": ("Aegean Airlines", "A3"),
    "OAL": ("Olympic Air", "OA"),
    "SKG": ("SKY express", "GQ"),
    # Nordics
    "SAS": ("Scandinavian Airlines", "SK"),
    "FIN": ("Finnair", "AY"),
    "NOZ": ("Norwegian Air Shuttle", "DY"),
    "NBT": ("Norse Atlantic", "N0"),
    "NSZ": ("Norwegian Air Sweden", "D8"),
    "ICE": ("Icelandair", "FI"),
    "PLM": ("Play", "OG"),
    # North America
    "DAL": ("Delta Air Lines", "DL"),
    "UAL": ("United Airlines", "UA"),
    "AAL": ("American Airlines", "AA"),
    "SWA": ("Southwest Airlines", "WN"),
    "JBU": ("JetBlue Airways", "B6"),
    "ASA": ("Alaska Airlines", "AS"),
    "ACA": ("Air Canada", "AC"),
    "WJA": ("WestJet", "WS"),
    "AMX": ("Aeromexico", "AM"),
    "VOI": ("Volaris", "Y4"),
    # South America
    "TAM": ("LATAM Airlines Brasil", "JJ"),
    "LAN": ("LATAM Airlines Chile", "LA"),
    "ARG": ("Aerolineas Argentinas", "AR"),
    "AVA": ("Avianca", "AV"),
    "GLO": ("GOL Linhas Aereas", "G3"),
    "AZU": ("Azul Brazilian Airlines", "AD"),
    # Asia Pacific
    "CPA": ("Cathay Pacific", "CX"),
    "CES": ("China Eastern Airlines", "MU"),
    "CSN": ("China Southern Airlines", "CZ"),
    "CCA": ("Air China", "CA"),
    "CHH": ("Hainan Airlines", "HU"),
    "SIA": ("Singapore Airlines", "SQ"),
    "ANA": ("All Nippon Airways", "NH"),
    "JAL": ("Japan Airlines", "JL"),
    "KAL": ("Korean Air", "KE"),
    "AAR": ("Asiana Airlines", "OZ"),
    "EVA": ("EVA Air", "BR"),
    "CAL": ("China Airlines", "CI"),
    "THA": ("Thai Airways", "TG"),
    "MAS": ("Malaysia Airlines", "MH"),
    "GIA": ("Garuda Indonesia", "GA"),
    "PAL": ("Philippine Airlines", "PR"),
    "AIC": ("Air India", "AI"),
    "IGO": ("IndiGo", "6E"),
    "VTI": ("Vistara", "UK"),
    "ALK": ("SriLankan Airlines", "UL"),
    "QFA": ("Qantas", "QF"),
    "ANZ": ("Air New Zealand", "NZ"),
    "JST": ("Jetstar Airways", "JQ"),
    "CSH": ("Shanghai Airlines", "FM"),
    "HYT": ("YTO Cargo Airlines", "YG"),
    "LHA": ("Air Central", "GI"),
    "CSC": ("Sichaun Airlines", "3U"),
    # Cargo
    "UPS": ("UPS Airlines", "5X"),
    "FDX": ("FedEx Express", "FX"),
    "GTI": ("Atlas Air", "5Y"),
    "DHK": ("DHL Air", "D0"),
    "BCS": ("European Air Transport (DHL)", "QY"),
    "CLX": ("Cargolux", "CV"),
    "MPH": ("Martinair Cargo", "MP"),
    "SQC": ("Singapore Airlines Cargo", "SQ"),
    "ABW": ("AirBridgeCargo", "RU"),
    "CKS": ("Kalitta Air", "K4"),
    "KZU": ("ULS Airlines Cargo", "GO"),
}


def _lookup(callsign: str | None) -> tuple[str, str | None] | None:
    if not callsign or len(callsign) < 3:
        return None
    prefix = callsign[:3].upper()
    return AIRLINES.get(prefix)


def airline_from_callsign(callsign: str | None) -> str | None:
    entry = _lookup(callsign)
    return entry[0] if entry else None


def airline_iata_from_callsign(callsign: str | None) -> str | None:
    entry = _lookup(callsign)
    return entry[1] if entry else None
