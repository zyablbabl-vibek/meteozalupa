import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { PointSummary } from "../types/weather";
import { PointsTable } from "./PointsTable";

const item: PointSummary = {
  point: { id: "x", name: "Серышево", latitude: 51, longitude: 128 },
  mean_temperature: 10,
  models: { "ECMWF IFS": 10, "NOAA GFS": 11, "DWD ICON": null },
  minimum: 10,
  maximum: 11,
  spread: 1,
  agreement: "высокое",
  precipitation: {
    count: 2,
    complete: false,
    consensus_available: true,
    mean: 2,
  },
  wind_speed: {
    count: 2,
    complete: false,
    consensus_available: true,
    mean: 3,
  },
  humidity: {
    count: 2,
    complete: false,
    consensus_available: true,
    mean: 60,
  },
  pressure: {
    count: 2,
    complete: false,
    consensus_available: true,
    mean: 1008,
  },
  max_gust: 5,
  precipitation_analysis: {
    daily_total: {
      count: 2,
      complete: false,
      consensus_available: true,
      model_values: {},
    },
    relative_spread_pct: null,
    hourly_peak: { count: 2, complete: false, consensus_available: true },
    peak_time: null,
    peak_model: null,
    peak_value: null,
    event_start: null,
    event_end: null,
    duration_hours: 0,
    event_count: 0,
    hours_above_threshold: 0,
    confirming_models: 0,
    start_time_disagreement_hours: null,
  },
  wind_analysis: {
    mean_speed: {
      count: 2,
      complete: false,
      consensus_available: true,
      model_values: {},
    },
    maximum_speed: {
      count: 2,
      complete: false,
      consensus_available: true,
      model_values: {},
    },
    maximum_gust: {
      count: 2,
      complete: false,
      consensus_available: true,
      model_values: {},
    },
    maximum_gust_time: null,
    maximum_gust_model: null,
    maximum_gust_value: null,
    circular_mean_direction_deg: null,
    direction_label: null,
    directions_by_model: {},
    direction_labels_by_model: {},
    maximum_direction_disagreement_deg: null,
    direction_disagreement_models: [],
    direction_agreement: "недостаточно данных",
    strong_wind_start: null,
    strong_wind_end: null,
    strong_wind_duration_hours: 0,
  },
  incomplete: true,
};

describe("PointsTable", () => {
  it("shows a missing model and selects the point", () => {
    const select = vi.fn();
    render(<PointsTable points={[item]} onSelect={select} />);
    expect(screen.getByText("неполно")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText("Серышево"));
    expect(select).toHaveBeenCalledWith("x");
  });
});
