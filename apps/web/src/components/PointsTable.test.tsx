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
