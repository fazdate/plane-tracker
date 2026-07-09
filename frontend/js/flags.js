// ---- Country flag emojis (fully local, no network calls) ----
//
// Two helpers:
//   flagEmoji(iso)              ISO 3166-1 alpha-2 code -> flag emoji
//   registrationCountryIso(reg) aircraft registration   -> ISO alpha-2 code
//
// Flag emojis are just the two "regional indicator" symbols for the country
// code, so any ISO alpha-2 code maps to a flag with no lookup table needed.
// Registration -> country uses the static ICAO nationality-prefix allocation
// below, so it needs no network call either.

// Turn a 2-letter ISO country code into its flag emoji, e.g. "HU" -> 🇭🇺.
// Returns "" for anything that isn't a plain 2-letter code.
export function flagEmoji(iso) {
  if (!iso || typeof iso !== "string") return "";
  const cc = iso.trim().toUpperCase();
  if (!/^[A-Z]{2}$/.test(cc)) return "";
  const A = 0x1f1e6; // regional indicator "A"
  return String.fromCodePoint(
    A + cc.charCodeAt(0) - 65,
    A + cc.charCodeAt(1) - 65,
  );
}

// ICAO nationality registration prefixes -> ISO 3166-1 alpha-2 country code.
// Keyed by the mark that precedes the hyphen (e.g. "HA-LVK" -> "HA"), or by
// the leading characters for the few schemes without a hyphen (US "N12345",
// Japan "JA8089", South Korea "HL7500"). A handful of "PREFIX-X" combo keys
// disambiguate territories that share a first mark (British "VP-"/"VQ-",
// Chinese "B-" vs Hong Kong / Macau).
const REG_PREFIX = {
  // --- No-hyphen schemes ---
  N: "US", JA: "JP", HL: "KR", B: "CN",

  // --- Chinese SAR / territory disambiguation (B-H..., B-M...) ---
  "B-H": "HK", "B-K": "HK", "B-L": "HK", "B-M": "MO",

  // --- Europe ---
  G: "GB", D: "DE", F: "FR", I: "IT", C: "CA",
  EC: "ES", CS: "PT", OO: "BE", PH: "NL", OY: "DK",
  SE: "SE", LN: "NO", OH: "FI", OE: "AT", HB: "CH",
  OK: "CZ", OM: "SK", SP: "PL", HA: "HU", YR: "RO",
  LZ: "BG", "9A": "HR", S5: "SI", YU: "RS", Z3: "MK",
  ZA: "AL", E7: "BA", "4O": "ME", LY: "LT", YL: "LV",
  ES: "EE", EI: "IE", EJ: "IE", SX: "GR", TC: "TR",
  "5B": "CY", "9H": "MT", LX: "LU", "3A": "MC", TF: "IS",
  EW: "BY", RA: "RU", RF: "RU", UR: "UA", "4K": "AZ",
  "4L": "GE", EK: "AM", EX: "KG", EY: "TJ", EZ: "TM",
  UN: "KZ", UP: "KZ", UK: "UZ",

  // --- Middle East ---
  "4X": "IL", JY: "JO", OD: "LB", HZ: "SA", A6: "AE",
  A7: "QA", A9C: "BH", "9K": "KW", YK: "SY", YI: "IQ",
  EP: "IR", A4O: "OM", "7O": "YE",

  // --- Asia ---
  AP: "PK", VT: "IN", "4R": "LK", S2: "BD", "9N": "NP",
  VN: "VN", HS: "TH", "9M": "MY", "9V": "SG", PK: "ID",
  RP: "PH", XU: "KH", XW: "LA", XY: "MM", "8Q": "MV",

  // --- Africa ---
  SU: "EG", ST: "SD", "5A": "LY", TS: "TN", "7T": "DZ",
  CN: "MA", ET: "ET", "5Y": "KE", "5H": "TZ", "5X": "UG",
  "9G": "GH", "5N": "NG", TU: "CI", "6V": "SN", "3X": "GN",
  ZS: "ZA", ZT: "ZA", ZU: "ZA", V5: "NA", A2: "BW",
  Z: "ZW", "9J": "ZM", C9: "MZ", "5R": "MG",

  // --- Americas ---
  LV: "AR", PP: "BR", PR: "BR", PT: "BR", PU: "BR",
  CC: "CL", HK: "CO", HC: "EC", CP: "BO", ZP: "PY",
  CX: "UY", YV: "VE", "8R": "GY", PZ: "SR",
  XA: "MX", XB: "MX", XC: "MX", TG: "GT", YS: "SV",
  HR: "HN", YN: "NI", TI: "CR", HP: "PA", CU: "CU",
  "6Y": "JM", C6: "BS", "9Y": "TT", HI: "DO", HH: "HT",

  // --- Oceania ---
  VH: "AU", ZK: "NZ", DQ: "FJ", P2: "PG",

  // --- British overseas territories (VP-x / VQ-x) ---
  "VP-A": "AI", "VP-B": "BM", "VQ-B": "BM", "VP-C": "KY",
  "VP-F": "FK", "VP-G": "GI", "VP-L": "VG", "VP-M": "MS",
  "VQ-T": "TC",
};

// Look up the ISO alpha-2 country code for an aircraft registration, or null.
export function registrationCountryIso(reg) {
  if (!reg || typeof reg !== "string") return null;
  const s = reg.toUpperCase().replace(/[^A-Z0-9-]/g, "");
  if (!s) return null;

  const dash = s.indexOf("-");
  if (dash > 0) {
    const prefix = s.slice(0, dash);
    const firstSuffix = s.slice(dash + 1, dash + 2);
    // Territory disambiguation first (VP-B, VQ-T, B-H, ...), then the mark.
    const combo = `${prefix}-${firstSuffix}`;
    if (REG_PREFIX[combo]) return REG_PREFIX[combo];
    if (REG_PREFIX[prefix]) return REG_PREFIX[prefix];
    return null;
  }

  // No hyphen (US "N", Japan "JA", South Korea "HL"): longest prefix wins.
  for (let len = 2; len >= 1; len--) {
    const p = s.slice(0, len);
    if (REG_PREFIX[p]) return REG_PREFIX[p];
  }
  return null;
}
