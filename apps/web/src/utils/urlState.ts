import type { Horizon, Section } from "../types/weather";
import { localDate } from "./format";

export function readForecastUrl(search = window.location.search): {
  horizon: Horizon;
  date: string;
  section: Section;
} {
  const params = new URLSearchParams(search);
  const raw = params.get("horizon");
  const horizon: Horizon =
    raw === "3d" || raw === "7d" || raw === "today" ? raw : "today";
  const rawSection = params.get("section");
  const section: Section =
    rawSection === "precipitation" || rawSection === "wind"
      ? rawSection
      : "temperature";
  return { horizon, date: params.get("date") || localDate(), section };
}

export function forecastUrl(
  horizon: Horizon,
  date: string,
  section: Section = "temperature",
): string {
  return `/?${new URLSearchParams({ horizon, date, section }).toString()}`;
}
