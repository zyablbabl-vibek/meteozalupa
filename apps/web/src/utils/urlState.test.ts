import { describe, expect, it } from "vitest";
import { forecastUrl, readForecastUrl } from "./urlState";

describe("forecast URL state", () => {
  it("reads horizon and selected date", () => {
    expect(
      readForecastUrl("?horizon=7d&date=2026-08-02&section=precipitation"),
    ).toEqual({
      region: "amur-oblast",
      horizon: "7d",
      date: "2026-08-02",
      section: "precipitation",
      view: "day",
      point: null,
    });
  });

  it("serializes horizon and selected date", () => {
    expect(
      forecastUrl({
        region: "primorsky-krai",
        horizon: "3d",
        date: "2026-07-31",
        section: "wind",
        view: "period",
        point: "vladivostok",
      }),
    ).toBe(
      "/?region=primorsky-krai&horizon=3d&date=2026-07-31&section=wind&view=period&point=vladivostok",
    );
  });
});
