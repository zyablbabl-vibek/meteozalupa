import { describe, expect, it } from "vitest";
import type { DailyModelSummary, DailySummary } from "../types/weather";
import { buildPeriodPrecipitationData } from "./periodPrecipitation";

const day = (
  date: string,
  ECMWF: number | null,
  GFS: number | null,
  ICON: number | null,
): DailySummary => {
  const model = (precipitation: number): DailyModelSummary => ({
    temperature_min: 10,
    temperature_max: 20,
    temperature_mean: 15,
    precipitation_sum: precipitation,
    wind_speed_mean: 3,
    wind_gust_max: 6,
  });
  return {
    date,
    available: true,
    precipitation_sum: null,
    mean_temperature: 15,
    minimum_temperature: 10,
    maximum_temperature: 20,
    mean_wind_speed: 3,
    max_gust: 6,
    mean_humidity: 70,
    mean_pressure: 1008,
    spread: 1,
    agreement: "высокое",
    models: {
      "ECMWF IFS": ECMWF == null ? null : model(ECMWF),
      "NOAA GFS": GFS == null ? null : model(GFS),
      "DWD ICON": ICON == null ? null : model(ICON),
    },
  };
};

describe("period precipitation chart data", () => {
  it("accumulates every model separately and builds model ranges", () => {
    const result = buildPeriodPrecipitationData([
      day("2026-08-01", 1, 2, 3),
      day("2026-08-02", 2, 3, 4),
    ]);

    expect(result[0].dailyBand).toEqual([1, 3]);
    expect(result[1].cumECMWF).toBe(3);
    expect(result[1].cumGFS).toBe(5);
    expect(result[1].cumICON).toBe(7);
    expect(result[1].cumulativeBand).toEqual([3, 7]);
    expect(result[1].cumulativeConsensus).toBe(5);
  });

  it("does not replace a missing model day with zero", () => {
    const result = buildPeriodPrecipitationData([
      day("2026-08-01", 1, 2, 3),
      day("2026-08-02", 2, 3, null),
      day("2026-08-03", 2, 3, 4),
    ]);

    expect(result[1].cumICON).toBeNull();
    expect(result[2].cumICON).toBeNull();
    expect(result[2].cumECMWF).toBe(5);
    expect(result[2].cumGFS).toBe(8);
    expect(result[2].cumulativeConsensus).toBe(6.5);
  });
});
