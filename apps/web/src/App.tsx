import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  getForecast,
  getInsights,
  getPointForecast,
  refreshForecast,
} from "./api/weather";
import { DayCards } from "./components/DayCards";
import { HorizonControl } from "./components/HorizonControl";
import { InsightsPanel } from "./components/InsightsPanel";
import { PeriodOverview } from "./components/PeriodOverview";
import { PointDetails } from "./components/PointDetails";
import { PointsTable } from "./components/PointsTable";
import { PrecipitationTable } from "./components/PrecipitationTable";
import { SectionControl } from "./components/SectionControl";
import { WeatherMap } from "./components/WeatherMap";
import { WindTable } from "./components/WindTable";
import type { Horizon, Section } from "./types/weather";
import { localDate, number, temperature } from "./utils/format";
import { forecastUrl, readForecastUrl } from "./utils/urlState";

type View = "day" | "period";

function writeUrl(
  horizon: Horizon,
  date: string,
  section: Section,
  replace = false,
) {
  const method = replace ? "replaceState" : "pushState";
  window.history[method](null, "", forecastUrl(horizon, date, section));
}

export default function App() {
  const initial = readForecastUrl();
  const [horizon, setHorizon] = useState<Horizon>(initial.horizon);
  const [date, setDate] = useState(initial.date);
  const [section, setSection] = useState<Section>(initial.section);
  const [view, setView] = useState<View>("day");
  const [selected, setSelected] = useState<string | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    const onPopState = () => {
      const state = readForecastUrl();
      setHorizon(state.horizon);
      setDate(state.date);
      setSection(state.section);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const forecast = useQuery({
    queryKey: ["forecast", horizon, date],
    queryFn: () => getForecast(horizon, date),
    retry: 1,
  });
  const details = useQuery({
    queryKey: ["point", selected, horizon, date],
    queryFn: () => getPointForecast(selected!, horizon, date),
    enabled: Boolean(selected) && view === "day",
  });
  const insights = useQuery({
    queryKey: ["insights", horizon, date],
    queryFn: () => getInsights(horizon, date),
    retry: 1,
  });
  const refresh = useMutation({
    mutationFn: refreshForecast,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["forecast"] }),
  });

  const changeHorizon = (next: Horizon) => {
    const today = localDate();
    setHorizon(next);
    setDate(today);
    setView("day");
    setSelected(null);
    writeUrl(next, today, section);
  };
  const changeDate = (next: string) => {
    setDate(next);
    setView("day");
    setSelected(null);
    writeUrl(horizon, next, section);
  };
  const changeSection = (next: Section) => {
    setSection(next);
    setSelected(null);
    writeUrl(horizon, date, next);
  };

  if (forecast.isLoading)
    return (
      <main className="state">
        <div className="loader" />
        <h1>Собираем прогнозы трёх моделей…</h1>
        <p>Загружаем единый семидневный набор.</p>
      </main>
    );
  if (forecast.isError)
    return (
      <main className="state error">
        <h1>Не удалось загрузить прогноз</h1>
        <p>{forecast.error.message}</p>
        <button onClick={() => forecast.refetch()}>Повторить</button>
      </main>
    );

  const data = forecast.data!;
  const avg =
    data.points.reduce((sum, point) => sum + point.mean_temperature, 0) /
    data.points.length;
  const min = Math.min(...data.points.map((point) => point.minimum));
  const max = Math.max(...data.points.map((point) => point.maximum));
  const rain =
    data.points.reduce(
      (sum, point) => sum + (point.precipitation.mean ?? 0),
      0,
    ) / data.points.length;
  const gust = Math.max(...data.points.map((point) => point.max_gust ?? 0));
  const lowCount = data.points.filter(
    (point) => point.agreement === "низкое",
  ).length;

  return (
    <div>
      <header>
        <div>
          <span className="eyebrow">Amur Weather Consensus</span>
          <h1>Прогноз по Амурской области</h1>
        </div>
        <button onClick={() => refresh.mutate()} disabled={refresh.isPending}>
          {refresh.isPending ? "Обновляем 7 дней…" : "Обновить данные"}
        </button>
      </header>
      <main>
        <div className="forecast-navigation">
          <HorizonControl value={horizon} onChange={changeHorizon} />
          {horizon !== "today" && (
            <div className="view-toggle">
              <button
                className={view === "day" ? "active" : ""}
                onClick={() => setView("day")}
              >
                Выбранный день
              </button>
              <button
                className={view === "period" ? "active" : ""}
                onClick={() => setView("period")}
              >
                Весь период
              </button>
            </div>
          )}
        </div>
        <SectionControl value={section} onChange={changeSection} />
        <DayCards
          days={data.daily_summaries}
          selected={data.selected_date}
          onSelect={changeDate}
        />
        <div className="status-row">
          <span className={`mode ${data.data_mode}`}>
            {data.data_mode === "mock"
              ? "Демонстрационные данные"
              : "Live-данные"}
          </span>
          <span>● ECMWF IFS</span>
          <span>● NOAA GFS</span>
          <span>● DWD ICON</span>
          <span className="updated">
            Обновлено{" "}
            {new Date(data.last_updated).toLocaleString("ru-RU", {
              timeZone: "Asia/Yakutsk",
            })}
          </span>
        </div>
        {data.warnings.length > 0 && (
          <div className="warning">{data.warnings.join(" · ")}</div>
        )}

        {view === "period" && horizon !== "today" ? (
          <PeriodOverview
            days={data.daily_summaries}
            summary={data.period_summary}
            section={section}
          />
        ) : (
          <>
            <section className="hero">
              <div>
                <span className="eyebrow">
                  Консенсус на{" "}
                  {new Intl.DateTimeFormat("ru-RU", {
                    day: "numeric",
                    month: "long",
                    timeZone: "Asia/Yakutsk",
                  }).format(new Date(`${data.selected_date}T03:00:00+09:00`))}
                </span>
                <h2>
                  {section === "temperature"
                    ? temperature(avg)
                    : section === "precipitation"
                      ? `${number(rain)} мм`
                      : `${number(
                          data.points.reduce(
                            (sum, point) => sum + (point.wind_speed.mean ?? 0),
                            0,
                          ) / data.points.length,
                        )} м/с`}
                </h2>
                <p>
                  {section === "temperature"
                    ? "Средняя температура по контрольным точкам"
                    : section === "precipitation"
                      ? "Средняя суточная сумма осадков"
                      : "Средняя скорость ветра"}
                </p>
              </div>
              <div className="cards">
                {section === "temperature" && (
                  <>
                    <article>
                      <span>Минимум</span>
                      <strong>{temperature(min)}</strong>
                    </article>
                    <article>
                      <span>Максимум</span>
                      <strong>{temperature(max)}</strong>
                    </article>
                    <article>
                      <span>Осадки</span>
                      <strong>{number(rain)} мм</strong>
                    </article>
                    <article>
                      <span>Макс. порыв</span>
                      <strong>{number(gust)} м/с</strong>
                    </article>
                    <article>
                      <span>Согласованность</span>
                      <strong>
                        {lowCount
                          ? `${lowCount} точек — низкая`
                          : "высокая / средняя"}
                      </strong>
                    </article>
                  </>
                )}
                {section === "precipitation" && (
                  <>
                    <article>
                      <span>Медиана</span>
                      <strong>
                        {number(
                          data.points.reduce(
                            (sum, point) =>
                              sum + (point.precipitation.median ?? 0),
                            0,
                          ) / data.points.length,
                        )}{" "}
                        мм
                      </strong>
                    </article>
                    <article>
                      <span>Максимум по области</span>
                      <strong>
                        {
                          data.points.reduce((a, b) =>
                            (a.precipitation.mean ?? 0) >
                            (b.precipitation.mean ?? 0)
                              ? a
                              : b,
                          ).point.name
                        }
                      </strong>
                    </article>
                    <article>
                      <span>Пиковая интенсивность</span>
                      <strong>
                        {number(
                          Math.max(
                            ...data.points.map(
                              (point) =>
                                point.precipitation_analysis.peak_value ?? 0,
                            ),
                          ),
                        )}{" "}
                        мм/ч
                      </strong>
                    </article>
                    <article>
                      <span>Макс. продолжительность</span>
                      <strong>
                        {Math.max(
                          ...data.points.map(
                            (point) =>
                              point.precipitation_analysis.duration_hours,
                          ),
                        )}{" "}
                        ч
                      </strong>
                    </article>
                    <article>
                      <span>Согласованность</span>
                      <strong>
                        {
                          data.points.filter(
                            (point) => point.precipitation.range! > 5,
                          ).length
                        }{" "}
                        точек требуют внимания
                      </strong>
                    </article>
                  </>
                )}
                {section === "wind" && (
                  <>
                    <article>
                      <span>Средняя скорость</span>
                      <strong>
                        {number(
                          data.points.reduce(
                            (sum, point) => sum + (point.wind_speed.mean ?? 0),
                            0,
                          ) / data.points.length,
                        )}{" "}
                        м/с
                      </strong>
                    </article>
                    <article>
                      <span>Максимальный порыв</span>
                      <strong>{number(gust)} м/с</strong>
                    </article>
                    <article>
                      <span>Источник порыва</span>
                      <strong>
                        {
                          data.points.reduce((a, b) =>
                            (a.max_gust ?? 0) > (b.max_gust ?? 0) ? a : b,
                          ).max_gust_source
                        }
                      </strong>
                    </article>
                    <article>
                      <span>Направление</span>
                      <strong>
                        {data.points[0].wind_analysis.direction_label ??
                          "Расходится"}
                      </strong>
                    </article>
                    <article>
                      <span>Угловой разброс</span>
                      <strong>
                        {number(
                          Math.max(
                            ...data.points.map(
                              (point) =>
                                point.wind_analysis
                                  .maximum_direction_disagreement_deg ?? 0,
                            ),
                          ),
                          0,
                        )}
                        °
                      </strong>
                    </article>
                  </>
                )}
              </div>
            </section>
            <section>
              <div className="section-heading">
                <div>
                  <span className="eyebrow">География прогноза</span>
                  <h2>Контрольные точки</h2>
                </div>
                <p>Размер маркера показывает расхождение моделей</p>
              </div>
              <WeatherMap
                points={data.points}
                onSelect={setSelected}
                section={section}
              />
            </section>
            <section>
              <div className="section-heading">
                <div>
                  <span className="eyebrow">Сравнение моделей</span>
                  <h2>Все точки</h2>
                </div>
                <p>Сортировка: максимальное расхождение</p>
              </div>
              {section === "temperature" && (
                <PointsTable points={data.points} onSelect={setSelected} />
              )}
              {section === "precipitation" && (
                <PrecipitationTable
                  points={data.points}
                  onSelect={setSelected}
                />
              )}
              {section === "wind" && (
                <WindTable points={data.points} onSelect={setSelected} />
              )}
            </section>
            {selected &&
              (details.isLoading ? (
                <div className="state compact">Загружаем подробности…</div>
              ) : details.data ? (
                <PointDetails
                  data={details.data}
                  dimPastHours={data.selected_date === localDate()}
                  section={section}
                />
              ) : (
                <div className="warning">Подробности недоступны</div>
              ))}
            {section === "temperature" && (
              <section className="extremes">
                <span className="eyebrow">Экстремумы выбранного дня</span>
                <h2>На что обратить внимание</h2>
                <div className="cards">
                  <article>
                    <span>Самая высокая температура</span>
                    <strong>
                      {
                        data.points.reduce((a, b) =>
                          a.maximum > b.maximum ? a : b,
                        ).point.name
                      }
                    </strong>
                    <small>
                      {temperature(max)} ·{" "}
                      {
                        data.points.reduce((a, b) =>
                          a.maximum > b.maximum ? a : b,
                        ).maximum_source
                      }
                    </small>
                  </article>
                  <article>
                    <span>Самая низкая температура</span>
                    <strong>
                      {
                        data.points.reduce((a, b) =>
                          a.minimum < b.minimum ? a : b,
                        ).point.name
                      }
                    </strong>
                    <small>
                      {temperature(min)} ·{" "}
                      {
                        data.points.reduce((a, b) =>
                          a.minimum < b.minimum ? a : b,
                        ).minimum_source
                      }
                    </small>
                  </article>
                  <article>
                    <span>Максимальные осадки</span>
                    <strong>
                      {
                        data.points.reduce((a, b) =>
                          (a.precipitation.mean ?? 0) >
                          (b.precipitation.mean ?? 0)
                            ? a
                            : b,
                        ).point.name
                      }
                    </strong>
                  </article>
                  <article>
                    <span>Максимальный порыв</span>
                    <strong>
                      {
                        data.points.reduce((a, b) =>
                          (a.max_gust ?? 0) > (b.max_gust ?? 0) ? a : b,
                        ).point.name
                      }
                    </strong>
                    <small>{number(gust)} м/с</small>
                  </article>
                  <article>
                    <span>Максимальное расхождение</span>
                    <strong>{data.points[0].point.name}</strong>
                    <small>{number(data.points[0].spread)} °C</small>
                  </article>
                </div>
              </section>
            )}
          </>
        )}
        {insights.data && (
          <InsightsPanel
            data={insights.data}
            category={section === "temperature" ? "all" : section}
          />
        )}
      </main>
      <footer>
        <p>
          Данные прогностических моделей:{" "}
          <a href="https://www.ecmwf.int/" target="_blank">
            ECMWF IFS
          </a>
          , NOAA GFS и DWD ICON. Доступ через{" "}
          <a href="https://open-meteo.com/" target="_blank">
            Open‑Meteo
          </a>
          .
        </p>
        <p>
          Прогноз рассчитан по контрольным точкам. Model agreement отражает
          только разброс моделей и не гарантирует точность.
        </p>
      </footer>
    </div>
  );
}
