import { describe, expect, it } from "vitest";
import { forecastUrl, readForecastUrl } from "./urlState";

describe("forecast URL state", () => {
  it("reads horizon and selected date", () => {
    expect(
      readForecastUrl("?horizon=7d&date=2026-08-02&section=precipitation"),
    ).toEqual({
      horizon: "7d",
      date: "2026-08-02",
      section: "precipitation",
    });
  });

  it("serializes horizon and selected date", () => {
    expect(forecastUrl("3d", "2026-07-31", "wind")).toBe(
      "/?horizon=3d&date=2026-07-31&section=wind",
    );
  });
});
