import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

vi.mock("../js/audio.js", () => ({
  playChime: vi.fn(),
}));

async function freshAlerts() {
  vi.resetModules();
  document.body.innerHTML = `
    <div id="alert-stack"></div>
    <div id="alert-flash"></div>
  `;
  const audio = await import("../js/audio.js");
  audio.playChime.mockClear();
  const alerts = await import("../js/alerts.js");
  return { alerts, playChime: audio.playChime };
}

function makeAircraft(overrides = {}) {
  return {
    icao24: "abc123",
    callsign: "TEST123",
    distance_km: 2,
    on_ground: false,
    alert: { level: "rare", reason: "Uncommon type" },
    ...overrides,
  };
}

beforeEach(() => {
  // requestAnimationFrame isn't implemented by jsdom by default; the banner
  // animation timing itself isn't under test here, so run it synchronously.
  global.requestAnimationFrame = (cb) => cb();
  // Avoid leaking the banner's real 7s/12s auto-dismiss setTimeout past the
  // end of each test.
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("processAlerts", () => {
  it("fires an alert once for a plane that enters the focus zone", async () => {
    const { alerts, playChime } = await freshAlerts();
    alerts.processAlerts([makeAircraft()], 10);
    expect(playChime).toHaveBeenCalledTimes(1);
    expect(playChime).toHaveBeenCalledWith("gold");
  });

  it("does not re-fire on subsequent updates for the same plane", async () => {
    const { alerts, playChime } = await freshAlerts();
    const ac = makeAircraft();
    alerts.processAlerts([ac], 10);
    alerts.processAlerts([ac], 10);
    alerts.processAlerts([ac], 10);
    expect(playChime).toHaveBeenCalledTimes(1);
  });

  it("uses the emergency chime kind for emergency-level alerts", async () => {
    const { alerts, playChime } = await freshAlerts();
    alerts.processAlerts([makeAircraft({ alert: { level: "emergency", reason: "Squawk 7700" } })], 10);
    expect(playChime).toHaveBeenCalledWith("emergency");
  });

  it("does not fire for aircraft without an alert", async () => {
    const { alerts, playChime } = await freshAlerts();
    alerts.processAlerts([makeAircraft({ alert: null })], 10);
    expect(playChime).not.toHaveBeenCalled();
  });

  it("does not fire for aircraft outside the focus radius", async () => {
    const { alerts, playChime } = await freshAlerts();
    alerts.processAlerts([makeAircraft({ distance_km: 50 })], 10);
    expect(playChime).not.toHaveBeenCalled();
  });

  it("does not fire for grounded aircraft", async () => {
    const { alerts, playChime } = await freshAlerts();
    alerts.processAlerts([makeAircraft({ on_ground: true })], 10);
    expect(playChime).not.toHaveBeenCalled();
  });

  it("re-fires after the plane leaves and re-enters the zone", async () => {
    const { alerts, playChime } = await freshAlerts();
    const ac = makeAircraft();
    alerts.processAlerts([ac], 10);
    alerts.processAlerts([], 10); // plane no longer present -> forgotten
    alerts.processAlerts([ac], 10); // re-enters -> should fire again

    expect(playChime).toHaveBeenCalledTimes(2);
  });

  it("appends a banner element to the alert stack", async () => {
    const { alerts } = await freshAlerts();
    alerts.processAlerts([makeAircraft()], 10);
    const stack = document.getElementById("alert-stack");
    expect(stack.children.length).toBe(1);
    expect(stack.children[0].className).toContain("alert-banner-item");
  });
});
