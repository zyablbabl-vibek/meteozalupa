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
import type { DailySummary, PeriodSummary, Section } from "../types/weather";
import { number, temperature } from "../utils/format";

const shortDate = (value: string) =>
  new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));

export function PeriodOverview({
  days,
  summary,
  section = "temperature",
}: {
  days: DailySummary[];
  summary: PeriodSummary;
  section?: Section;
}) {
  const cumulative: Record<"ECMWF" | "GFS" | "ICON" | "mean", number | null> = {
    ECMWF: null,
    GFS: null,
    ICON: null,
    mean: null,
  };
  const accumulate = (current: number | null, next: number | null) =>
    next == null ? current : current == null ? next : current + next;
  const data = days.map((day) => {
    const ECMWF = day.models["ECMWF IFS"]?.precipitation_sum ?? null;
    const GFS = day.models["NOAA GFS"]?.precipitation_sum ?? null;
    const ICON = day.models["DWD ICON"]?.precipitation_sum ?? null;
    cumulative.ECMWF = accumulate(cumulative.ECMWF, ECMWF);
    cumulative.GFS = accumulate(cumulative.GFS, GFS);
    cumulative.ICON = accumulate(cumulative.ICON, ICON);
    cumulative.mean = accumulate(cumulative.mean, day.precipitation_sum);
    return {
      date: shortDate(day.date),
      min: day.minimum_temperature,
      max: day.maximum_temperature,
      mean: day.mean_temperature,
      ECMWF,
      GFS,
      ICON,
      rain: day.precipitation_sum,
      cumECMWF: cumulative.ECMWF,
      cumGFS: cumulative.GFS,
      cumICON: cumulative.ICON,
      cumMean: cumulative.mean,
      windECMWF: day.models["ECMWF IFS"]?.wind_speed_mean,
      windGFS: day.models["NOAA GFS"]?.wind_speed_mean,
      windICON: day.models["DWD ICON"]?.wind_speed_mean,
      gustECMWF: day.models["ECMWF IFS"]?.wind_gust_max,
      gustGFS: day.models["NOAA GFS"]?.wind_gust_max,
      gustICON: day.models["DWD ICON"]?.wind_gust_max,
      wind: day.mean_wind_speed,
      gust: day.max_gust,
    };
  });
  return (
    <section className="period-overview">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Весь период</span>
          <h2>
            {section === "temperature"
              ? "Температура по дням"
              : section === "precipitation"
                ? "Осадки по дням"
                : "Ветер по дням"}
          </h2>
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
        {section === "temperature" && (
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
        )}
        {section === "precipitation" && (
          <>
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
              <h3>Накопительные осадки</h3>
              <div className="small-chart">
                <ResponsiveContainer>
                  <ComposedChart data={data}>
                    <XAxis dataKey="date" />
                    <YAxis unit=" мм" />
                    <Tooltip />
                    <Legend />
                    <Line
                      dataKey="cumECMWF"
                      name="ECMWF накоплено"
                      stroke="#326789"
                    />
                    <Line
                      dataKey="cumGFS"
                      name="GFS накоплено"
                      stroke="#c87a34"
                    />
                    <Line
                      dataKey="cumICON"
                      name="ICON накоплено"
                      stroke="#71864b"
                    />
                    <Line
                      dataKey="cumMean"
                      name="Среднее накоплено"
                      stroke="#173b45"
                      strokeWidth={3}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </article>
          </>
        )}
        {section === "wind" && (
          <>
            <article>
              <h3>Средняя скорость по моделям</h3>
              <div className="small-chart">
                <ResponsiveContainer>
                  <ComposedChart data={data}>
                    <XAxis dataKey="date" />
                    <YAxis unit=" м/с" />
                    <Tooltip />
                    <Legend />
                    <Line dataKey="windECMWF" name="ECMWF" stroke="#326789" />
                    <Line dataKey="windGFS" name="GFS" stroke="#c87a34" />
                    <Line dataKey="windICON" name="ICON" stroke="#71864b" />
                    <Line
                      dataKey="wind"
                      name="Среднее"
                      stroke="#173b45"
                      strokeWidth={3}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </article>
            <article>
              <h3>Максимальные порывы по моделям</h3>
              <div className="small-chart">
                <ResponsiveContainer>
                  <BarChart data={data}>
                    <XAxis dataKey="date" />
                    <YAxis unit=" м/с" />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="gustECMWF" name="ECMWF" fill="#326789" />
                    <Bar dataKey="gustGFS" name="GFS" fill="#c87a34" />
                    <Bar dataKey="gustICON" name="ICON" fill="#71864b" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>
          </>
        )}
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
