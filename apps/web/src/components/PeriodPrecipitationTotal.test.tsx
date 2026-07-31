import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { PeriodSummary } from "../types/weather";
import { PeriodPrecipitationTotal } from "./PeriodPrecipitationTotal";

const precipitation: PeriodSummary["precipitation"] = {
  point: {
    id: "ola",
    region_id: "magadan-oblast",
    name: "Ола",
    latitude: 59.58,
    longitude: 151.3,
    timezone: "Asia/Magadan",
    point_type: "settlement",
    is_regional_center: false,
    weight: 1,
  },
  models: {
    "ECMWF IFS": 4.8,
    "NOAA GFS": 5.2,
    "DWD ICON": 5.6,
  },
  statistics: {
    count: 3,
    complete: true,
    consensus_available: true,
    mean: 5.2,
  },
};
const regional: PeriodSummary["regional_precipitation"] = {
  models: {
    "ECMWF IFS": 2.8,
    "NOAA GFS": 3.4,
    "DWD ICON": 4.1,
  },
  statistics: {
    count: 3,
    complete: true,
    consensus_available: true,
    mean: 3.433,
  },
  expected_days: 3,
  model_day_counts: {
    "ECMWF IFS": 3,
    "NOAA GFS": 3,
    "DWD ICON": 3,
  },
  method: "weighted_spatial_mean_then_period_sum",
};

describe("PeriodPrecipitationTotal", () => {
  it("shows the 3-day consensus and each model total", () => {
    render(
      <PeriodPrecipitationTotal
        dayCount={3}
        regional={regional}
        wettestPoint={precipitation}
      />,
    );

    expect(screen.getByText("Суммарные осадки за 3 дня")).toBeInTheDocument();
    expect(screen.getByText("3.4 мм")).toBeInTheDocument();
    expect(
      screen.getByText("Среднее накопление по контрольным точкам региона"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("ECMWF 2.8 мм · GFS 3.4 мм · ICON 4.1 мм"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Максимум в отдельной точке/)).toHaveTextContent(
      "5.2 мм · Ола",
    );
  });

  it("uses the correct label for a 7-day period", () => {
    render(
      <PeriodPrecipitationTotal
        dayCount={7}
        regional={regional}
        wettestPoint={precipitation}
      />,
    );
    expect(screen.getByText("Суммарные осадки за 7 дней")).toBeInTheDocument();
  });
});
