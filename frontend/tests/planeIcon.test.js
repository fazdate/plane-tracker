import { describe, it, expect } from "vitest";
import { altitudeColor, colorForClass, classFor } from "../js/planeIcon.js";

describe("altitudeColor", () => {
  it("returns the default fill color when altitude is unknown", () => {
    expect(altitudeColor(null)).toBe("#ffe14d");
    expect(altitudeColor(undefined)).toBe("#ffe14d");
  });

  it("returns a warm red/orange hue near the low end of the range", () => {
    expect(altitudeColor(0)).toBe("hsl(0, 100%, 60%)");
  });

  it("returns a magenta/pink hue near the high end of the range", () => {
    expect(altitudeColor(11000)).toBe("hsl(355, 100%, 60%)");
  });

  it("clamps altitudes below the configured minimum", () => {
    expect(altitudeColor(-5000)).toBe(altitudeColor(0));
  });

  it("clamps altitudes above the configured maximum", () => {
    expect(altitudeColor(50000)).toBe(altitudeColor(11000));
  });
});

describe("colorForClass", () => {
  it("returns a fixed color for known special-state classes", () => {
    expect(colorForClass("emergency")).toBe("var(--red)");
    expect(colorForClass("focused")).toBe("#ffffff");
    expect(colorForClass("interesting")).toBe("var(--gold)");
    expect(colorForClass("grounded")).toBe("var(--text-dim)");
  });

  it("returns null for the default/unknown class so altitude color is used instead", () => {
    expect(colorForClass("")).toBeNull();
    expect(colorForClass("something-else")).toBeNull();
  });
});

describe("classFor", () => {
  it("prioritizes emergency alerts over everything else", () => {
    const ac = { alert: { level: "emergency" }, icao24: "abc", on_ground: true };
    expect(classFor(ac, "abc")).toBe("emergency");
  });

  it("marks the focused aircraft when it has no emergency alert", () => {
    const ac = { icao24: "abc", on_ground: false };
    expect(classFor(ac, "abc")).toBe("focused");
  });

  it("marks interesting (uncommon-type) aircraft below focused priority", () => {
    const ac = { alert: { level: "interesting" }, icao24: "abc" };
    expect(classFor(ac, "other")).toBe("interesting");
  });

  it("marks grounded aircraft when nothing else applies", () => {
    const ac = { icao24: "abc", on_ground: true };
    expect(classFor(ac, "other")).toBe("grounded");
  });

  it("returns an empty string for a plain airborne aircraft", () => {
    const ac = { icao24: "abc", on_ground: false };
    expect(classFor(ac, "other")).toBe("");
  });
});
