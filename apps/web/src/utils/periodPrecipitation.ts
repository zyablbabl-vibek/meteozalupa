import type { DailySummary } from "../types/weather";

export const PRECIPITATION_MODELS = [
  {
    key: "ECMWF IFS",
    dataKey: "ECMWF",
    label: "ECMWF",
    color: "#2f6f9f",
    background: "#edf5fb",
    description: "Европейский центр среднесрочных прогнозов",
  },
  {
    key: "NOAA GFS",
    dataKey: "GFS",
    label: "GFS",
    color: "#d47a2a",
    background: "#fff4e8",
    description: "Глобальная система прогнозов NOAA",
  },
  {
    key: "DWD ICON",
    dataKey: "ICON",
    label: "ICON",
    color: "#718d3d",
    background: "#f2f6e9",
    description: "Глобальная модель метеослужбы DWD",
  },
] as const;

type ModelDataKey = (typeof PRECIPITATION_MODELS)[number]["dataKey"];

const consensus = (items: Array<number | null>) => {
  const available = items.filter((item): item is number => item != null);
  return available.length >= 2
    ? available.reduce((sum, value) => sum + value, 0) / available.length
    : null;
};

const range = (items: Array<number | null>): [number, number] | null => {
  const available = items.filter((item): item is number => item != null);
  return available.length >= 2
    ? [Math.min(...available), Math.max(...available)]
    : null;
};

export function buildPeriodPrecipitationData(days: DailySummary[]) {
  const cumulative = Object.fromEntries(
    PRECIPITATION_MODELS.map((model) => [
      model.dataKey,
      { value: 0, complete: true },
    ]),
  ) as Record<ModelDataKey, { value: number; complete: boolean }>;

  return days.map((day) => {
    const daily = Object.fromEntries(
      PRECIPITATION_MODELS.map((model) => [
        model.dataKey,
        day.models[model.key]?.precipitation_sum ?? null,
      ]),
    ) as Record<ModelDataKey, number | null>;

    const cumulativeValues = Object.fromEntries(
      PRECIPITATION_MODELS.map((model) => {
        const state = cumulative[model.dataKey];
        const value = daily[model.dataKey];
        if (value == null || !state.complete) {
          state.complete = false;
          return [`cum${model.dataKey}`, null];
        }
        state.value += value;
        return [`cum${model.dataKey}`, state.value];
      }),
    ) as Record<`cum${ModelDataKey}`, number | null>;
    const cumulativeAvailable = PRECIPITATION_MODELS.map(
      (model) => cumulativeValues[`cum${model.dataKey}`],
    );
    const dailyAvailable = PRECIPITATION_MODELS.map(
      (model) => daily[model.dataKey],
    );

    return {
      date: day.date,
      ...daily,
      dailyConsensus: consensus(dailyAvailable),
      dailyBand: range(dailyAvailable),
      ...cumulativeValues,
      cumulativeConsensus: consensus(cumulativeAvailable),
      cumulativeBand: range(cumulativeAvailable),
    };
  });
}
