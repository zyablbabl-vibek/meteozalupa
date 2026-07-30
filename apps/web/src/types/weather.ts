export type Horizon = "today" | "3d" | "7d";
export type ModelValues = Record<string, number | null>;
export type Statistics = {
  count: number;
  complete: boolean;
  consensus_available: boolean;
  mean?: number;
  median?: number | null;
  minimum?: number;
  minimum_source?: string;
  maximum?: number;
  maximum_source?: string;
  range?: number;
  standard_deviation?: number;
};
export type Point = {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
};
export type PointSummary = {
  point: Point;
  mean_temperature: number;
  models: ModelValues;
  minimum: number;
  minimum_source?: string;
  maximum: number;
  maximum_source?: string;
  spread: number;
  agreement: string;
  precipitation: Statistics;
  wind_speed: Statistics;
  humidity: Statistics;
  pressure: Statistics;
  max_gust: number | null;
  max_gust_source?: string;
  incomplete: boolean;
};
export type Hourly = {
  point_id: string;
  point_name: string;
  forecast_time_local: string;
  models: ModelValues;
  statistics: Statistics;
  agreement: string;
};
export type DailyModelSummary = {
  temperature_min: number;
  temperature_max: number;
  temperature_mean: number;
  precipitation_sum: number;
  wind_speed_mean: number;
  wind_gust_max: number;
};
export type DailySummary = {
  date: string;
  available: boolean;
  mean_temperature: number;
  minimum_temperature: number;
  maximum_temperature: number;
  precipitation_sum: number;
  mean_wind_speed: number;
  max_gust: number;
  mean_humidity: number;
  mean_pressure: number;
  spread: number;
  agreement: string;
  models: Record<string, DailyModelSummary | null>;
};
export type Extreme = {
  value: number;
  unit: string;
  date: string;
  forecast_time: string;
  point_name: string;
  model: string;
};
export type PeriodSummary = {
  period_start: string;
  period_end: string;
  warmest_day: DailySummary;
  coldest_day: DailySummary;
  wettest_day: DailySummary;
  gustiest_day: DailySummary;
  most_divergent_day: DailySummary;
  temperature: {
    absolute_maximum: Extreme;
    absolute_minimum: Extreme;
    mean: number;
  };
  precipitation: {
    point: Point;
    models: Record<string, number | null>;
    statistics: Statistics;
  };
  wind: {
    maximum_speed: Extreme;
    maximum_gust: Extreme;
    circular_mean_direction: number | null;
  };
};
export type Forecast = {
  horizon: Horizon;
  period_start: string;
  period_end: string;
  selected_date: string;
  available_dates: string[];
  data_mode: "mock" | "live";
  warnings: string[];
  last_updated: string;
  points: PointSummary[];
  hourly: Hourly[];
  daily_summaries: DailySummary[];
  period_summary: PeriodSummary;
};
export type PointForecast = {
  point: Point;
  horizon: Horizon;
  selected_date: string;
  available_dates: string[];
  series: Record<string, Hourly[]>;
  daily_aggregates: Array<Record<string, string | number | null>>;
  period_summary: PeriodSummary;
  warnings: string[];
};
