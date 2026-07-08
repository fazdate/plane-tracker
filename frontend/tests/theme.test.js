import { describe, it, expect, beforeEach, vi } from "vitest";

async function freshTheme() {
  vi.resetModules();
  return import("../js/theme.js");
}

beforeEach(() => {
  document.body.className = "";
});

describe("applyTheme", () => {
  it("adds theme-day and removes theme-night for daytime", async () => {
    const { applyTheme } = await freshTheme();
    applyTheme(true);
    expect(document.body.classList.contains("theme-day")).toBe(true);
    expect(document.body.classList.contains("theme-night")).toBe(false);
  });

  it("adds theme-night and removes theme-day for nighttime", async () => {
    const { applyTheme } = await freshTheme();
    applyTheme(false);
    expect(document.body.classList.contains("theme-night")).toBe(true);
    expect(document.body.classList.contains("theme-day")).toBe(false);
  });

  it("is a no-op when given null/undefined (avoids flashing the wrong theme)", async () => {
    const { applyTheme } = await freshTheme();
    applyTheme(null);
    expect(document.body.classList.contains("theme-day")).toBe(false);
    expect(document.body.classList.contains("theme-night")).toBe(false);
  });

  it("skips redundant DOM updates when the value hasn't changed", async () => {
    const { applyTheme } = await freshTheme();
    applyTheme(true);
    const spy = vi.spyOn(document.body.classList, "toggle");
    applyTheme(true); // same value again
    expect(spy).not.toHaveBeenCalled();
  });

  it("updates again when the value actually flips", async () => {
    const { applyTheme } = await freshTheme();
    applyTheme(true);
    applyTheme(false);
    expect(document.body.classList.contains("theme-night")).toBe(true);
    expect(document.body.classList.contains("theme-day")).toBe(false);
  });
});

describe("applyInitialGuess", () => {
  function mockMatchMedia(matches) {
    window.matchMedia = vi.fn().mockImplementation((query) => ({
      matches,
      media: query,
      addListener: vi.fn(),
      removeListener: vi.fn(),
    }));
  }

  it("applies the light theme when the OS prefers light", async () => {
    mockMatchMedia(true);
    const { applyInitialGuess } = await freshTheme();
    applyInitialGuess();
    expect(document.body.classList.contains("theme-day")).toBe(true);
  });

  it("applies the dark theme when the OS does not prefer light", async () => {
    mockMatchMedia(false);
    const { applyInitialGuess } = await freshTheme();
    applyInitialGuess();
    expect(document.body.classList.contains("theme-night")).toBe(true);
  });
});
