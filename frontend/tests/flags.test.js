import { describe, it, expect } from "vitest";
import { flagEmoji, registrationCountryIso } from "../js/flags.js";

describe("flagEmoji", () => {
  it("converts a 2-letter ISO code to its flag emoji", () => {
    expect(flagEmoji("HU")).toBe("🇭🇺");
    expect(flagEmoji("US")).toBe("🇺🇸");
    expect(flagEmoji("gb")).toBe("🇬🇧"); // case-insensitive
  });

  it("returns an empty string for invalid input", () => {
    expect(flagEmoji("")).toBe("");
    expect(flagEmoji(null)).toBe("");
    expect(flagEmoji("USA")).toBe("");
    expect(flagEmoji("1U")).toBe("");
  });
});

describe("registrationCountryIso", () => {
  it("maps hyphenated nationality marks to ISO codes", () => {
    expect(registrationCountryIso("HA-LVK")).toBe("HU");
    expect(registrationCountryIso("D-AIMA")).toBe("DE");
    expect(registrationCountryIso("G-EUYA")).toBe("GB");
    expect(registrationCountryIso("9A-CTK")).toBe("HR");
    expect(registrationCountryIso("EC-MXG")).toBe("ES");
  });

  it("handles no-hyphen schemes (US, Japan, South Korea)", () => {
    expect(registrationCountryIso("N7018A")).toBe("US");
    expect(registrationCountryIso("JA8089")).toBe("JP");
    expect(registrationCountryIso("HL7500")).toBe("KR");
  });

  it("disambiguates shared first marks", () => {
    expect(registrationCountryIso("B-2087")).toBe("CN"); // mainland China
    expect(registrationCountryIso("B-HUJ")).toBe("HK"); // Hong Kong
    expect(registrationCountryIso("B-MAV")).toBe("MO"); // Macau
    expect(registrationCountryIso("VP-BAA")).toBe("BM"); // Bermuda
    expect(registrationCountryIso("VP-CXX")).toBe("KY"); // Cayman
  });

  it("returns null for empty or unknown prefixes", () => {
    expect(registrationCountryIso("")).toBe(null);
    expect(registrationCountryIso(null)).toBe(null);
    expect(registrationCountryIso("QQ-ZZZ")).toBe(null);
  });
});
