import { describe, it, expect, beforeAll } from "vitest";
import { altitudeColor, colorForClass, classFor, makePlaneIcon } from "../js/planeIcon.js";

// makePlaneIcon() calls Leaflet's L.divIcon(); stub it so these tests can
// run without pulling in the real Leaflet library.
beforeAll(() => {
  globalThis.L = { divIcon: (opts) => opts };
});

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
    expect(colorForClass("rare")).toBe("var(--gold)");
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

  it("marks rare (uncommon-type) aircraft below focused priority", () => {
    const ac = { alert: { level: "rare" }, icao24: "abc" };
    expect(classFor(ac, "other")).toBe("rare");
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

describe("makePlaneIcon", () => {
  it("uses the plane icon and class by default", () => {
    const icon = makePlaneIcon(90, "", 5000);
    expect(icon.className).toBe("plane-icon ");
    expect(icon.html).not.toContain("<line");
  });

  it("uses a helicopter icon and adds a helicopter class when requested", () => {
    const icon = makePlaneIcon(90, "", 5000, true);
    expect(icon.className).toBe("plane-icon helicopter ");
    expect(icon.html).toContain("<line");
  });

  it("rotates the icon to match heading, defaulting to 0 when missing", () => {
    const icon = makePlaneIcon(null, "", 5000);
    expect(icon.html).toContain("rotate(0deg)");
  });
});
