import type {
  Forecast,
  Horizon,
  InsightsResponse,
  PointForecast,
  Region,
} from "../types/weather";
import type { GeoJsonObject } from "geojson";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 90_000;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(
    () => controller.abort(),
    REQUEST_TIMEOUT_MS,
  );
  try {
    const response = await fetch(`${BASE}${path}`, {
      ...init,
      signal: controller.signal,
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(
        payload.detail ||
          payload.error?.message ||
          "Сервис прогноза недоступен",
      );
    }
    return response.json();
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(
        "Сервер не ответил за 90 секунд. Повторите запрос — сохранённые данные не потеряны.",
      );
    }
    throw error;
  } finally {
    window.clearTimeout(timeout);
  }
}

const params = (regionId: string, horizon: Horizon, date?: string) => {
  const value = new URLSearchParams({ region_id: regionId, horizon });
  if (date) value.set("date", date);
  return value.toString();
};

export const getRegions = () => request<{ regions: Region[] }>("/api/regions");
export const getRegion = (regionId: string) =>
  request<Region>(`/api/regions/${regionId}`);
export const getRegionGeoJson = (regionId: string) =>
  request<GeoJsonObject>(`/api/regions/${regionId}/geojson`);
export const getForecast = (
  regionId: string,
  horizon: Horizon,
  date?: string,
) =>
  request<Forecast>(
    `/api/forecast?${params(regionId, horizon, date)}&metric=temperature_2m`,
  );
export const getPointForecast = (
  regionId: string,
  id: string,
  horizon: Horizon,
  date?: string,
) =>
  request<PointForecast>(
    `/api/forecast/${id}?${params(regionId, horizon, date)}`,
  );
export const refreshForecast = (regionId: string) =>
  request(`/api/refresh?region_id=${encodeURIComponent(regionId)}`, {
    method: "POST",
  });
export const getInsights = (
  regionId: string,
  horizon: Horizon,
  date?: string,
) =>
  request<InsightsResponse>(`/api/insights?${params(regionId, horizon, date)}`);
