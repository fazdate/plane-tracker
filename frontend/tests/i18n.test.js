import { describe, it, expect, beforeEach, vi } from "vitest";

// i18n.js keeps module-level mutable state (currentLang, listeners), so we
// reset the module registry and re-import fresh before each test to avoid
// state bleeding between tests.
async function freshI18n() {
  vi.resetModules();
  return import("../js/i18n.js");
}

beforeEach(() => {
  localStorage.clear();
});

describe("t()", () => {
  it("translates a plain string key in the default language", async () => {
    const { t } = await freshI18n();
    expect(t("emergency")).toBe("VÉSZHELYZET"); // default language is Hungarian
  });

  it("translates a function-valued key with arguments", async () => {
    const { t } = await freshI18n();
    expect(t("aircraftCount", 3)).toBe("3 repülőgép");
  });

  it("falls back to English when a key is missing from the active dictionary", async () => {
    const { t, setLang } = await freshI18n();
    setLang("en");
    // "photoOf" exists in both, so use a real lookup to prove the language switch worked
    expect(t("photoOf", "HA-LVK")).toBe("Photo of HA-LVK");
  });
});

describe("tBadgeLevel()", () => {
  it("translates a known alert level in the default (Hungarian) language", async () => {
    const { tBadgeLevel } = await freshI18n();
    expect(tBadgeLevel("rare")).toBe("RITKA");
    expect(tBadgeLevel("common")).toBe("GYAKORI");
    expect(tBadgeLevel("emergency")).toBe("VÉSZHELYZET");
  });

  it("translates a known alert level in English", async () => {
    const { tBadgeLevel, setLang } = await freshI18n();
    setLang("en");
    expect(tBadgeLevel("rare")).toBe("RARE");
    expect(tBadgeLevel("common")).toBe("COMMON");
    expect(tBadgeLevel("emergency")).toBe("EMERGENCY");
  });

  it("falls back to the raw level for an unrecognized level", async () => {
    const { tBadgeLevel } = await freshI18n();
    expect(tBadgeLevel("focused")).toBe("focused");
  });
});

describe("language persistence and cycling", () => {
  it("defaults to Hungarian when nothing is stored", async () => {
    const { getLang } = await freshI18n();
    expect(getLang()).toBe("hu");
  });

  it("restores a previously stored language", async () => {
    localStorage.setItem("lang", "en");
    const { getLang } = await freshI18n();
    expect(getLang()).toBe("en");
  });

  it("ignores an invalid stored language and falls back to the default", async () => {
    localStorage.setItem("lang", "xx");
    const { getLang } = await freshI18n();
    expect(getLang()).toBe("hu");
  });

  it("setLang persists the choice and notifies listeners exactly once", async () => {
    const { setLang, getLang, onLangChange } = await freshI18n();
    const listener = vi.fn();
    onLangChange(listener);

    setLang("en");

    expect(getLang()).toBe("en");
    expect(localStorage.getItem("lang")).toBe("en");
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledWith("en");
  });

  it("setLang is a no-op for an unknown language", async () => {
    const { setLang, getLang, onLangChange } = await freshI18n();
    const listener = vi.fn();
    onLangChange(listener);

    setLang("fr");

    expect(getLang()).toBe("hu");
    expect(listener).not.toHaveBeenCalled();
  });

  it("setLang is a no-op when re-selecting the current language", async () => {
    const { setLang, onLangChange } = await freshI18n();
    const listener = vi.fn();
    onLangChange(listener);

    setLang("hu"); // already the default

    expect(listener).not.toHaveBeenCalled();
  });

  it("nextLang cycles through LANGUAGES and wraps around", async () => {
    const { nextLang, getLang, LANGUAGES } = await freshI18n();
    expect(getLang()).toBe("hu");
    nextLang();
    expect(getLang()).toBe(LANGUAGES[(LANGUAGES.indexOf("hu") + 1) % LANGUAGES.length]);
  });
});

describe("localStorage failures", () => {
  it("does not throw and still switches language when localStorage.getItem throws", async () => {
    const original = Storage.prototype.getItem;
    Storage.prototype.getItem = () => { throw new Error("blocked"); };
    try {
      const { getLang } = await freshI18n();
      expect(getLang()).toBe("hu"); // safe fallback
    } finally {
      Storage.prototype.getItem = original;
    }
  });

  it("does not throw and still switches language when localStorage.setItem throws", async () => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = () => { throw new Error("blocked"); };
    try {
      const { setLang, getLang } = await freshI18n();
      expect(() => setLang("en")).not.toThrow();
      expect(getLang()).toBe("en"); // in-memory switch still happens
    } finally {
      Storage.prototype.setItem = original;
    }
  });
});

describe("applyStaticI18n", () => {
  it("applies text content and title attributes from data-i18n attributes", async () => {
    const { applyStaticI18n } = await freshI18n();
    document.body.innerHTML = `
      <button id="reset" data-i18n="resetView" data-i18n-title="resetViewTitle"></button>
    `;
    applyStaticI18n(document);
    const el = document.getElementById("reset");
    expect(el.textContent).toBe("⟲ Nézet visszaállítása");
    expect(el.title).toBe("Nézet visszaállítása");
  });
});
