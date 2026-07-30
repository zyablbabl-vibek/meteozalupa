import type { Horizon, Section, View } from "../types/weather";
import { localDate } from "./format";

export const DEFAULT_REGION_ID = "amur-oblast";

export type ForecastUrlState = {
  region: string;
  horizon: Horizon;
  date: string;
  section: Section;
  view: View;
  point: string | null;
};

export function readForecastUrl(
  search = window.location.search,
): ForecastUrlState {
  const params = new URLSearchParams(search);
  const rawHorizon = params.get("horizon");
  const horizon: Horizon =
    rawHorizon === "3d" || rawHorizon === "7d" || rawHorizon === "today"
      ? rawHorizon
      : "today";
  const rawSection = params.get("section");
  const section: Section =
    rawSection === "precipitation" || rawSection === "wind"
      ? rawSection
      : "temperature";
  return {
    region: params.get("region") || DEFAULT_REGION_ID,
    horizon,
    date: params.get("date") || localDate(),
    section,
    view: params.get("view") === "period" ? "period" : "day",
    point: params.get("point"),
  };
}

export function forecastUrl(state: ForecastUrlState): string {
  const params = new URLSearchParams({
    region: state.region,
    horizon: state.horizon,
    date: state.date,
    section: state.section,
    view: state.view,
  });
  if (state.point) params.set("point", state.point);
  return `/?${params.toString()}`;
}
