import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { DailySummary } from "../types/weather";
import { DayCards } from "./DayCards";

const day = (date: string): DailySummary => ({
  date,
  available: true,
  mean_temperature: 10,
  minimum_temperature: 2,
  maximum_temperature: 16,
  precipitation_sum: 3,
  mean_wind_speed: 4,
  max_gust: 8,
  mean_humidity: 60,
  mean_pressure: 1008,
  spread: 1,
  agreement: "высокое",
  models: {},
});

describe("DayCards", () => {
  it.each([1, 3, 7])("renders %i calendar days and selects one", (count) => {
    const select = vi.fn();
    const days = Array.from({ length: count }, (_, index) => {
      const value = new Date("2026-07-30T00:00:00Z");
      value.setUTCDate(value.getUTCDate() + index);
      return day(value.toISOString().slice(0, 10));
    });
    render(<DayCards days={days} selected={days[0].date} onSelect={select} />);
    expect(screen.getAllByRole("button")).toHaveLength(count);
    fireEvent.click(screen.getAllByRole("button")[count - 1]);
    expect(select).toHaveBeenCalledWith(days[count - 1].date);
  });
});
