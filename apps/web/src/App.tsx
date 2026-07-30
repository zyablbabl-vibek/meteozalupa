import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import {
  getForecast,
  getInsights,
  getPointForecast,
  getRegionGeoJson,
  getRegions,
  refreshForecast,
} from "./api/weather";
import { DayCards } from "./components/DayCards";
import { HorizonControl } from "./components/HorizonControl";
import { InsightsPanel } from "./components/InsightsPanel";
import { PeriodOverview } from "./components/PeriodOverview";
import { PointDetails } from "./components/PointDetails";
import { PointsTable } from "./components/PointsTable";
import { PrecipitationTable } from "./components/PrecipitationTable";
import { RegionHeader } from "./components/RegionHeader";
import { RegionMap } from "./components/RegionMap";
import {
  RegionCoverageNotice,
  RegionErrorState,
  RegionLoadingState,
  RegionTimezoneNotice,
} from "./components/RegionNotices";
import { SectionControl } from "./components/SectionControl";
import { WindTable } from "./components/WindTable";
import type {
  Horizon,
  PointForecast,
  Region,
  Section,
  View,
} from "./types/weather";
import { localDate, number, temperature } from "./utils/format";
import {
  DEFAULT_REGION_ID,
  type ForecastUrlState,
  forecastUrl,
  readForecastUrl,
} from "./utils/urlState";

const horizonDays: Record<Horizon, number> = { today: 1, "3d": 3, "7d": 7 };

function dateForRegion(region: Region, horizon: Horizon, requested: string) {
  const start = localDate(region.primary_timezone);
  const end = new Date(`${start}T00:00:00Z`);
  end.setUTCDate(end.getUTCDate() + horizonDays[horizon] - 1);
  const endValue = end.toISOString().slice(0, 10);
  return requested >= start && requested <= endValue ? requested : start;
}

function values(items: Array<number | null | undefined>) {
  return items.filter((item): item is number => item != null);
}

function average(items: Array<number | null | undefined>) {
  const available = values(items);
  return available.length
    ? available.reduce((sum, value) => sum + value, 0) / available.length
    : null;
}

function maximum(items: Array<number | null | undefined>) {
  const available = values(items);
  return available.length ? Math.max(...available) : null;
}

function minimum(items: Array<number | null | undefined>) {
  const available = values(items);
  return available.length ? Math.min(...available) : null;
}

function replaceUrl(state: ForecastUrlState, replace = false) {
  window.history[replace ? "replaceState" : "pushState"](
    null,
    "",
    forecastUrl(state),
  );
}

export default function App() {
  const initial = useMemo(() => readForecastUrl(), []);
  const [regionId, setRegionId] = useState(initial.region);
  const [horizon, setHorizon] = useState<Horizon>(initial.horizon);
  const [date, setDate] = useState(initial.date);
  const [section, setSection] = useState<Section>(initial.section);
  const [view, setView] = useState<View>(initial.view);
  const [selected, setSelected] = useState<string | null>(initial.point);
  const [urlNotice, setUrlNotice] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const regionsQuery = useQuery({
    queryKey: ["regions"],
    queryFn: getRegions,
    staleTime: Number.POSITIVE_INFINITY,
  });
  const region = regionsQuery.data?.regions.find(
    (item) => item.id === regionId,
  );

  useEffect(() => {
    const onPopState = () => {
      const state = readForecastUrl();
      setRegionId(state.region);
      setHorizon(state.horizon);
      setDate(state.date);
      setSection(state.section);
      setView(state.view);
      setSelected(state.point);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  useEffect(() => {
    if (!regionsQuery.data || region) return;
    const fallback =
      regionsQuery.data.regions.find((item) => item.id === DEFAULT_REGION_ID) ??
      regionsQuery.data.regions[0];
    if (!fallback) return;
    const nextDate = dateForRegion(fallback, horizon, date);
    setUrlNotice(`Регион «${regionId}» не найден. Выбрана ${fallback.name}.`);
    setRegionId(fallback.id);
    setDate(nextDate);
    setSelected(fallback.default_point_id);
    replaceUrl(
      {
        region: fallback.id,
        horizon,
        date: nextDate,
        section,
        view,
        point: fallback.default_point_id,
      },
      true,
    );
  }, [date, horizon, region, regionId, regionsQuery.data, section, view]);

  useEffect(() => {
    if (!region || selected) return;
    setSelected(region.default_point_id);
    replaceUrl(
      {
        region: region.id,
        horizon,
        date,
        section,
        view,
        point: region.default_point_id,
      },
      true,
    );
  }, [date, horizon, region, section, selected, view]);

  const forecast = useQuery({
    queryKey: ["forecast", region?.id, horizon, date],
    queryFn: () => getForecast(region!.id, horizon, date),
    enabled: Boolean(region),
    retry: 1,
  });
  const geojson = useQuery({
    queryKey: ["region-geojson", region?.id],
    queryFn: () => getRegionGeoJson(region!.id),
    enabled: Boolean(region?.geojson_available),
    staleTime: Number.POSITIVE_INFINITY,
  });
  const details = useQuery({
    queryKey: ["point", region?.id, selected, horizon, date],
    queryFn: () => getPointForecast(region!.id, selected!, horizon, date),
    enabled: Boolean(region && selected) && view === "day",
  });
  const insights = useQuery({
    queryKey: ["insights", region?.id, horizon, date],
    queryFn: () => getInsights(region!.id, horizon, date),
    enabled: Boolean(region),
    retry: 1,
  });
  const refresh = useMutation({
    mutationFn: refreshForecast,
    onSuccess: (_response, refreshedRegionId) => {
      queryClient.invalidateQueries({
        queryKey: ["forecast", refreshedRegionId],
      });
      queryClient.invalidateQueries({
        queryKey: ["insights", refreshedRegionId],
      });
      queryClient.invalidateQueries({ queryKey: ["point", refreshedRegionId] });
    },
  });

  if (regionsQuery.isLoading) {
    return (
      <main className="state">
        <div className="loader" />
        <h1>Загружаем регионы Дальнего Востока…</h1>
      </main>
    );
  }
  if (regionsQuery.isError || !regionsQuery.data) {
    return (
      <main className="state error">
        <h1>Не удалось загрузить список регионов</h1>
        <p>{regionsQuery.error?.message}</p>
        <button onClick={() => regionsQuery.refetch()}>Повторить</button>
      </main>
    );
  }
  if (!region) return null;

  const changeRegion = (nextId: string) => {
    const next = regionsQuery.data.regions.find((item) => item.id === nextId);
    if (!next) return;
    const nextDate = dateForRegion(next, horizon, date);
    setUrlNotice(null);
    setRegionId(next.id);
    setDate(nextDate);
    setSelected(next.default_point_id);
    replaceUrl({
      region: next.id,
      horizon,
      date: nextDate,
      section,
      view,
      point: next.default_point_id,
    });
  };

  const changeHorizon = (next: Horizon) => {
    const nextDate = dateForRegion(region, next, date);
    setHorizon(next);
    setDate(nextDate);
    setView("day");
    replaceUrl({
      region: region.id,
      horizon: next,
      date: nextDate,
      section,
      view: "day",
      point: selected,
    });
  };

  const changeDate = (next: string) => {
    setDate(next);
    setView("day");
    replaceUrl({
      region: region.id,
      horizon,
      date: next,
      section,
      view: "day",
      point: selected,
    });
  };

  const changeSection = (next: Section) => {
    setSection(next);
    replaceUrl({
      region: region.id,
      horizon,
      date,
      section: next,
      view,
      point: selected,
    });
  };

  const changeView = (next: View) => {
    setView(next);
    replaceUrl({
      region: region.id,
      horizon,
      date,
      section,
      view: next,
      point: selected,
    });
  };

  const selectPoint = (pointId: string) => {
    setSelected(pointId);
    replaceUrl({
      region: region.id,
      horizon,
      date,
      section,
      view,
      point: pointId,
    });
  };

  return (
    <div>
      <RegionHeader
        regions={regionsQuery.data.regions}
        region={region}
        lastUpdated={forecast.data?.last_updated}
        dataMode={forecast.data?.data_mode}
        modelAvailability={forecast.data?.model_availability}
        refreshing={refresh.isPending}
        onRegionChange={changeRegion}
        onRefresh={() => refresh.mutate(region.id)}
      />
      <main>
        <div className="forecast-navigation">
          <HorizonControl value={horizon} onChange={changeHorizon} />
          {horizon !== "today" && (
            <div className="view-toggle">
              <button
                className={view === "day" ? "active" : ""}
                onClick={() => changeView("day")}
              >
                Выбранный день
              </button>
              <button
                className={view === "period" ? "active" : ""}
                onClick={() => changeView("period")}
              >
                Весь период
              </button>
            </div>
          )}
        </div>
        <SectionControl value={section} onChange={changeSection} />
        {urlNotice && <div className="warning">{urlNotice}</div>}
        <RegionCoverageNotice region={region} />
        <RegionTimezoneNotice region={region} />

        {forecast.isLoading ? (
          <RegionLoadingState name={region.name} />
        ) : forecast.isError ? (
          <RegionErrorState
            message={forecast.error.message}
            onRetry={() => forecast.refetch()}
          />
        ) : forecast.data ? (
          <ForecastBody
            data={forecast.data}
            region={region}
            horizon={horizon}
            section={section}
            view={view}
            selected={selected}
            details={details}
            insights={insights.data}
            geojson={geojson.data}
            onDateChange={changeDate}
            onPointSelect={selectPoint}
          />
        ) : null}
      </main>
      <footer>
        <p>
          Данные ECMWF IFS, NOAA GFS и DWD ICON доступны через Open‑Meteo.
          Координаты контрольных точек: GeoNames, CC BY 4.0.
        </p>
        <p>
          Прогноз рассчитан по контрольным точкам выбранного региона. Согласие
          моделей отражает разброс, а не гарантированную точность.
        </p>
      </footer>
    </div>
  );
}

function ForecastBody({
  data,
  region,
  horizon,
  section,
  view,
  selected,
  details,
  insights,
  geojson,
  onDateChange,
  onPointSelect,
}: {
  data: Awaited<ReturnType<typeof getForecast>>;
  region: Region;
  horizon: Horizon;
  section: Section;
  view: View;
  selected: string | null;
  details: UseQueryResult<PointForecast, Error>;
  insights: Awaited<ReturnType<typeof getInsights>> | undefined;
  geojson: Awaited<ReturnType<typeof getRegionGeoJson>> | undefined;
  onDateChange: (date: string) => void;
  onPointSelect: (pointId: string) => void;
}) {
  if (!data.points.length) {
    return (
      <RegionErrorState
        message="Для региона нет достаточного количества модельных данных."
        onRetry={() => window.location.reload()}
      />
    );
  }

  const avgTemperature = average(
    data.points.map((point) => point.mean_temperature),
  );
  const minTemperature = minimum(data.points.map((point) => point.minimum));
  const maxTemperature = maximum(data.points.map((point) => point.maximum));
  const meanRain = average(
    data.points.map((point) => point.precipitation.mean),
  );
  const meanWind = average(data.points.map((point) => point.wind_speed.mean));
  const maxGust = maximum(data.points.map((point) => point.max_gust));
  const lowAgreement = data.points.filter(
    (point) => point.agreement === "низкое",
  ).length;

  if (view === "period" && horizon !== "today") {
    return (
      <>
        <DayCards
          days={data.daily_summaries}
          selected={data.selected_date}
          onSelect={onDateChange}
        />
        <PeriodOverview
          days={data.daily_summaries}
          summary={data.period_summary}
          section={section}
        />
        {insights && (
          <InsightsPanel
            data={insights}
            category={section === "temperature" ? "all" : section}
          />
        )}
      </>
    );
  }

  return (
    <>
      <DayCards
        days={data.daily_summaries}
        selected={data.selected_date}
        onSelect={onDateChange}
      />
      <div className="status-row">
        <span>● ECMWF IFS</span>
        <span>● NOAA GFS</span>
        <span>● DWD ICON</span>
        <span>{region.point_count} контрольных точек</span>
        {!region.geojson_available && (
          <span>Граница GeoJSON не подключена — показаны точки</span>
        )}
      </div>
      {data.warnings.length > 0 && (
        <div className="warning">{data.warnings.join(" · ")}</div>
      )}
      <section className="hero">
        <div>
          <span className="eyebrow">
            Консенсус на{" "}
            {new Intl.DateTimeFormat("ru-RU", {
              day: "numeric",
              month: "long",
              timeZone: region.primary_timezone,
            }).format(new Date(`${data.selected_date}T12:00:00Z`))}
          </span>
          <h2>
            {section === "temperature"
              ? temperature(avgTemperature)
              : section === "precipitation"
                ? `${number(meanRain)} мм`
                : `${number(meanWind)} м/с`}
          </h2>
          <p>
            {section === "temperature"
              ? "Средняя температура по контрольным точкам"
              : section === "precipitation"
                ? "Средняя суточная сумма осадков"
                : "Средняя скорость ветра"}
          </p>
        </div>
        <div className="cards regional-kpis">
          <article>
            <span>Минимум</span>
            <strong>{temperature(minTemperature)}</strong>
          </article>
          <article>
            <span>Максимум</span>
            <strong>{temperature(maxTemperature)}</strong>
          </article>
          <article>
            <span>Осадки</span>
            <strong>{number(meanRain)} мм</strong>
          </article>
          <article>
            <span>Макс. порыв</span>
            <strong>{number(maxGust)} м/с</strong>
          </article>
          <article>
            <span>Согласованность</span>
            <strong>
              {lowAgreement
                ? `${lowAgreement} точек — низкая`
                : "высокая / средняя"}
            </strong>
          </article>
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
        <RegionMap
          key={region.id}
          region={region}
          geojson={geojson}
          points={data.points}
          onSelect={onPointSelect}
          section={section}
        />
      </section>
      <section>
        <div className="section-heading">
          <div>
            <span className="eyebrow">Сравнение моделей</span>
            <h2>Все точки {region.name_genitive}</h2>
          </div>
        </div>
        {section === "temperature" && (
          <PointsTable points={data.points} onSelect={onPointSelect} />
        )}
        {section === "precipitation" && (
          <PrecipitationTable points={data.points} onSelect={onPointSelect} />
        )}
        {section === "wind" && (
          <WindTable points={data.points} onSelect={onPointSelect} />
        )}
      </section>
      {selected &&
        (details.isLoading ? (
          <div className="state compact">Загружаем подробности…</div>
        ) : details.data ? (
          <PointDetails
            data={details.data}
            dimPastHours={
              data.selected_date === localDate(region.primary_timezone)
            }
            section={section}
          />
        ) : (
          <div className="warning">Подробности точки недоступны</div>
        ))}
      {insights && (
        <InsightsPanel
          data={insights}
          category={section === "temperature" ? "all" : section}
        />
      )}
    </>
  );
}
