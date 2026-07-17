// ---- Minimal i18n: language dictionaries, persistence & toggle ----
const STORAGE_KEY = "lang";

const DICTS = {
  en: {
    labelAirline: "Airline",
    labelAircraft: "Aircraft",
    labelReg: "Reg",
    labelSeen: "Seen",
    labelRoute: "Route",
    labelAltitude: "Altitude",
    labelSpeed: "Speed",
    labelDistance: "Distance",
    resetView: "⟲ Reset View",
    resetViewTitle: "Reset view",
    connecting: "Connecting…",
    emergency: "EMERGENCY",
    rareAircraft: "RARE AIRCRAFT",
    aircraftPhoto: "Aircraft photo",
    langToggleTitle: "Language",
    weatherToggleTitle: "Weather radar",
    aircraftCount: (n) => `${n} aircraft`,
    dailyCount: (n) => `${n} airplanes tracked today`,
    dailyCountTitle: "Distinct aircraft tracked since midnight (local time)",
    photoOf: (reg) => `Photo of ${reg}`,
    firstTimeSeen: "First time seen!",
    timesSeen: (n) => `Seen ${n} times before`,
    routeUncertainTitle: "Route may be inaccurate - unverified against a second source",
    badgeLevel: {
      emergency: "EMERGENCY",
      rare: "RARE",
      common: "COMMON",
    },
  },
  hu: {
    labelAirline: "Légitársaság",
    labelAircraft: "Típus",
    labelReg: "Lajstromjel",
    labelSeen: "Látva",
    labelRoute: "Útvonal",
    labelAltitude: "Magasság",
    labelSpeed: "Sebesség",
    labelDistance: "Távolság",
    resetView: "⟲ Nézet visszaállítása",
    resetViewTitle: "Nézet visszaállítása",
    connecting: "Kapcsolódás…",
    emergency: "VÉSZHELYZET",
    rareAircraft: "RITKA REPÜLŐGÉP",
    aircraftPhoto: "Repülőgép fotó",
    langToggleTitle: "Nyelv",
    weatherToggleTitle: "Időjárás radar",
    aircraftCount: (n) => `${n} repülőgép`,
    dailyCount: (n) => `${n} repülőgép nyomon követve ma`,
    dailyCountTitle: "Éjfél (helyi idő) óta nyomon követett különböző repülőgépek száma",
    photoOf: (reg) => `Fénykép: ${reg}`,
    firstTimeSeen: "Most látjuk először!",
    timesSeen: (n) => `Korábban már ${n} alkalommal látva`,
    routeUncertainTitle: "Az útvonal pontatlan lehet - nem erősítette meg egy második forrás",
    badgeLevel: {
      emergency: "VÉSZHELYZET",
      rare: "RITKA",
      common: "GYAKORI",
    },
  },
};

// Order also defines the toggle's cycle order.
export const LANGUAGES = Object.keys(DICTS);

// Some browsers (private browsing, locked-down tablets/kiosk profiles, etc.)
// throw when touching localStorage at all, or only on writes once quota is
// zeroed out. Persistence is a nice-to-have, so never let it block the
// actual language switch from happening.
function readStoredLang() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch (e) {
    return null;
  }
}

function writeStoredLang(lang) {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch (e) {
    // Ignore: language still switches for this session, just isn't remembered.
  }
}

function detectDefault() {
  const saved = readStoredLang();
  if (saved && DICTS[saved]) return saved;
  return "hu"; // app defaults to Hungarian (Budapest-focused tracker)
}

let currentLang = detectDefault();
const listeners = new Set();

export function getLang() {
  return currentLang;
}

export function setLang(lang) {
  if (!DICTS[lang] || lang === currentLang) return;
  currentLang = lang;
  writeStoredLang(lang);
  for (const fn of listeners) fn(currentLang);
}

// Cycles to the next available language; used by the toggle button.
export function nextLang() {
  const idx = LANGUAGES.indexOf(currentLang);
  setLang(LANGUAGES[(idx + 1) % LANGUAGES.length]);
}

// Called whenever the language changes, so modules can refresh dynamic text.
export function onLangChange(fn) {
  listeners.add(fn);
}

export function t(key, ...args) {
  const dict = DICTS[currentLang] || DICTS.en;
  let entry = dict[key];
  if (entry === undefined) entry = DICTS.en[key];
  return typeof entry === "function" ? entry(...args) : entry;
}

// Translates an alert badge level (e.g. "emergency", "rare", "common") to the
// current language, falling back to the raw level if it's unrecognized.
export function tBadgeLevel(level) {
  const dict = DICTS[currentLang] || DICTS.en;
  return (dict.badgeLevel && dict.badgeLevel[level]) ||
    (DICTS.en.badgeLevel && DICTS.en.badgeLevel[level]) ||
    level;
}

// Applies translations to any static markup tagged with data-i18n /
// data-i18n-title attributes (labels, button text, tooltips, etc.).
export function applyStaticI18n(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  root.querySelectorAll("[data-i18n-title]").forEach((el) => {
    el.title = t(el.dataset.i18nTitle);
  });
}
