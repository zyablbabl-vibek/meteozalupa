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
import {
  PRECIPITATION_MODELS,
  buildPeriodPrecipitationData,
} from "../utils/periodPrecipitation";
import { PeriodPrecipitationTotal } from "./PeriodPrecipitationTotal";

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
  const precipitationData = buildPeriodPrecipitationData(days);
  const data = days.map((day, index) => {
    const precipitation = precipitationData[index];
    return {
      ...precipitation,
      date: shortDate(precipitation.date),
      min: day.minimum_temperature,
      max: day.maximum_temperature,
      mean: day.mean_temperature,
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
  const regionalPrecipitation = summary.regional_precipitation;
  const regionalConsensus = regionalPrecipitation.statistics.mean;
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
            <div className="model-comparison">
              <div className="chart-method-note">
                <strong>Как читать графики</strong>
                <span>
                  Цвет — отдельная модель, светлая зона — диапазон между
                  минимальной и максимальной оценкой, тёмная линия — консенсус.
                  Осадки усредняются по контрольным точкам, а не складываются
                  между ними.
                </span>
              </div>
              <div className="model-comparison-grid">
                {PRECIPITATION_MODELS.map((model) => {
                  const value = regionalPrecipitation.models[model.key];
                  const difference =
                    value != null && regionalConsensus != null
                      ? value - regionalConsensus
                      : null;
                  const differencePercent =
                    difference != null &&
                    regionalConsensus != null &&
                    regionalConsensus !== 0
                      ? (difference / regionalConsensus) * 100
                      : null;
                  return (
                    <article
                      key={model.key}
                      className="model-comparison-card"
                      style={{
                        borderColor: model.color,
                        background: model.background,
                      }}
                    >
                      <span
                        className="model-color"
                        style={{ background: model.color }}
                      />
                      <div>
                        <b>{model.label}</b>
                        <small>{model.description}</small>
                        <strong>{number(value)} мм</strong>
                        <small>
                          {difference == null
                            ? "Недостаточно данных за весь период"
                            : Math.abs(difference) < 0.05
                              ? "Совпадает с консенсусом"
                              : `${difference >= 0 ? "+" : ""}${number(
                                  difference,
                                )} мм (${difference >= 0 ? "+" : ""}${number(
                                  differencePercent,
                                  0,
                                )}%) к консенсусу`}
                        </small>
                      </div>
                    </article>
                  );
                })}
              </div>
            </div>
            <article>
              <h3>Средняя суточная сумма по региону</h3>
              <div className="small-chart">
                <ResponsiveContainer>
                  <ComposedChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis unit=" мм" domain={[0, "auto"]} />
                    <Tooltip />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="dailyBand"
                      name="Диапазон моделей"
                      stroke="#c5b99f"
                      fill="#e8e2d5"
                      fillOpacity={0.8}
                    />
                    {PRECIPITATION_MODELS.map((model) => (
                      <Bar
                        key={model.key}
                        dataKey={model.dataKey}
                        name={model.label}
                        fill={model.color}
                        fillOpacity={0.78}
                        maxBarSize={20}
                      />
                    ))}
                    <Line
                      type="monotone"
                      dataKey="dailyConsensus"
                      name="Консенсус"
                      stroke="#173b45"
                      strokeWidth={3}
                      dot={{ r: 3 }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <p className="chart-caption">
                Столбцы показывают среднюю суточную сумму каждой модели по
                контрольным точкам региона.
              </p>
            </article>
            <article>
              <h3>Накопление за выбранный период</h3>
              <div className="small-chart">
                <ResponsiveContainer>
                  <ComposedChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis unit=" мм" domain={[0, "auto"]} />
                    <Tooltip />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="cumulativeBand"
                      name="Диапазон моделей"
                      stroke="#b8c9c5"
                      fill="#dce9e5"
                      fillOpacity={0.78}
                    />
                    <Line
                      dataKey="cumECMWF"
                      name="ECMWF"
                      stroke={PRECIPITATION_MODELS[0].color}
                      strokeWidth={2}
                    />
                    <Line
                      dataKey="cumGFS"
                      name="GFS"
                      stroke={PRECIPITATION_MODELS[1].color}
                      strokeWidth={2}
                    />
                    <Line
                      dataKey="cumICON"
                      name="ICON"
                      stroke={PRECIPITATION_MODELS[2].color}
                      strokeWidth={2}
                    />
                    <Line
                      dataKey="cumulativeConsensus"
                      name="Консенсус после накопления"
                      stroke="#173b45"
                      strokeWidth={3.5}
                      dot={{ r: 3 }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <p className="chart-caption">
                Каждая модель накапливается отдельно. Пропущенный день не
                подменяется нулём; итоговый консенсус строится после
                суммирования.
              </p>
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
        <PeriodPrecipitationTotal
          dayCount={days.length}
          regional={summary.regional_precipitation}
          wettestPoint={summary.precipitation}
        />
      </div>
    </section>
  );
}
