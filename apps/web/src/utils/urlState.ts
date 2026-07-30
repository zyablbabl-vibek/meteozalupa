import type { Horizon } from "../types/weather";
import { localDate } from "./format";

export function readForecastUrl(search = window.location.search): {
  horizon: Horizon;
  date: string;
} {
  const params = new URLSearchParams(search);
  const raw = params.get("horizon");
  const horizon: Horizon =
    raw === "3d" || raw === "7d" || raw === "today" ? raw : "today";
  return { horizon, date: params.get("date") || localDate() };
}

export function forecastUrl(horizon: Horizon, date: string): string {
  return `/?${new URLSearchParams({ horizon, date }).toString()}`;
}
