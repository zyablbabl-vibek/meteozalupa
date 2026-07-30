import type { Forecast, Horizon, PointForecast } from "../types/weather";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(
      payload.detail || payload.error?.message || "Сервис прогноза недоступен",
    );
  }
  return response.json();
}

const params = (horizon: Horizon, date?: string) => {
  const value = new URLSearchParams({ horizon });
  if (date) value.set("date", date);
  return value.toString();
};

export const getForecast = (horizon: Horizon, date?: string) =>
  request<Forecast>(
    `/api/forecast?${params(horizon, date)}&metric=temperature_2m`,
  );
export const getPointForecast = (id: string, horizon: Horizon, date?: string) =>
  request<PointForecast>(`/api/forecast/${id}?${params(horizon, date)}`);
export const refreshForecast = () =>
  request("/api/refresh", { method: "POST" });
