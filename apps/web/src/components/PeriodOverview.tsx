import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DailySummary, PeriodSummary } from "../types/weather";
import { number, temperature } from "../utils/format";

const shortDate = (value: string) =>
  new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    timeZone: "Asia/Yakutsk",
  }).format(new Date(`${value}T03:00:00+09:00`));

export function PeriodOverview({
  days,
  summary,
}: {
  days: DailySummary[];
  summary: PeriodSummary;
}) {
  const data = days.map((day) => ({
    date: shortDate(day.date),
    min: day.minimum_temperature,
    max: day.maximum_temperature,
    mean: day.mean_temperature,
    ECMWF: day.models["ECMWF IFS"]?.precipitation_sum,
    GFS: day.models["NOAA GFS"]?.precipitation_sum,
    ICON: day.models["DWD ICON"]?.precipitation_sum,
    rain: day.precipitation_sum,
    wind: day.mean_wind_speed,
    gust: day.max_gust,
  }));
  return (
    <section className="period-overview">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Весь период</span>
          <h2>Динамика по дням</h2>
        </div>
      </div>
      <div className="period-kpis cards">
        <article>
          <span>Самый тёплый день</span>
          <strong>{shortDate(summary.warmest_day.date)}</strong>
          <small>{temperature(summary.warmest_day.mean_temperature)}</small>
        </article>
        <article>
          <span>Самый холодный день</span>
          <strong>{shortDate(summary.coldest_day.date)}</strong>
          <small>{temperature(summary.coldest_day.mean_temperature)}</small>
        </article>
        <article>
          <span>Максимальные осадки</span>
          <strong>{shortDate(summary.wettest_day.date)}</strong>
          <small>{number(summary.wettest_day.precipitation_sum)} мм</small>
        </article>
        <article>
          <span>Максимальный порыв</span>
          <strong>{shortDate(summary.gustiest_day.date)}</strong>
          <small>{number(summary.gustiest_day.max_gust)} м/с</small>
        </article>
        <article>
          <span>Наибольший разброс</span>
          <strong>{shortDate(summary.most_divergent_day.date)}</strong>
          <small>{number(summary.most_divergent_day.spread)} °C</small>
        </article>
      </div>
      <div className="overview-charts">
        <article>
          <h3>Температура</h3>
          <div className="small-chart">
            <ResponsiveContainer>
              <ComposedChart data={data}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis unit="°" />
                <Tooltip />
                <Area dataKey="max" fill="#e8b866" stroke="#c98436" />
                <Line dataKey="min" stroke="#3f7fa4" />
                <Line dataKey="mean" stroke="#173b45" strokeWidth={3} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </article>
        <article>
          <h3>Осадки по моделям</h3>
          <div className="small-chart">
            <ResponsiveContainer>
              <ComposedChart data={data}>
                <XAxis dataKey="date" />
                <YAxis unit=" мм" />
                <Tooltip />
                <Legend />
                <Line dataKey="ECMWF" stroke="#326789" />
                <Line dataKey="GFS" stroke="#c87a34" />
                <Line dataKey="ICON" stroke="#71864b" />
                <Line
                  dataKey="rain"
                  name="Среднее"
                  stroke="#173b45"
                  strokeWidth={3}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </article>
        <article>
          <h3>Ветер</h3>
          <div className="small-chart">
            <ResponsiveContainer>
              <BarChart data={data}>
                <XAxis dataKey="date" />
                <YAxis unit=" м/с" />
                <Tooltip />
                <Legend />
                <Bar dataKey="wind" name="Средняя скорость" fill="#4e8a80" />
                <Bar dataKey="gust" name="Макс. порыв" fill="#b65b3a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </div>
      <div className="period-extremes">
        <p>
          Абсолютный максимум:{" "}
          <strong>
            {temperature(summary.temperature.absolute_maximum.value)} ·{" "}
            {summary.temperature.absolute_maximum.point_name} ·{" "}
            {summary.temperature.absolute_maximum.model}
          </strong>
        </p>
        <p>
          Абсолютный минимум:{" "}
          <strong>
            {temperature(summary.temperature.absolute_minimum.value)} ·{" "}
            {summary.temperature.absolute_minimum.point_name} ·{" "}
            {summary.temperature.absolute_minimum.model}
          </strong>
        </p>
        <p>
          Осадки за период:{" "}
          <strong>
            {number(summary.precipitation.statistics.mean)} мм ·{" "}
            {summary.precipitation.point.name}
          </strong>
        </p>
      </div>
    </section>
  );
}
