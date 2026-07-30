import { useMemo, useState } from "react";
import type { PointSummary } from "../types/weather";
import { number } from "../utils/format";
import { AgreementBadge } from "./AgreementBadge";

type Sort = "mean" | "spread";

export function PrecipitationTable({
  points,
  onSelect,
}: {
  points: PointSummary[];
  onSelect: (id: string) => void;
}) {
  const [sort, setSort] = useState<Sort>("mean");
  const [attentionOnly, setAttentionOnly] = useState(false);
  const rows = useMemo(
    () =>
      points
        .filter(
          (point) =>
            !attentionOnly ||
            point.precipitation_analysis.daily_total.range! >= 10 ||
            (point.precipitation_analysis.peak_value ?? 0) >= 3,
        )
        .sort((a, b) =>
          sort === "mean"
            ? (b.precipitation.mean ?? -1) - (a.precipitation.mean ?? -1)
            : (b.precipitation.range ?? -1) - (a.precipitation.range ?? -1),
        ),
    [points, attentionOnly, sort],
  );
  const value = (point: PointSummary, model: string) =>
    point.precipitation_analysis.daily_total.model_values[model];
  return (
    <>
      <div className="table-tools">
        <label>
          Сортировка{" "}
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as Sort)}
          >
            <option value="mean">По средней сумме</option>
            <option value="spread">По разбросу</option>
          </select>
        </label>
        <label>
          <input
            type="checkbox"
            checked={attentionOnly}
            onChange={(event) => setAttentionOnly(event.target.checked)}
          />{" "}
          Только точки, требующие внимания
        </label>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Населённый пункт</th>
              <th>Среднее</th>
              <th>Медиана</th>
              <th>ECMWF</th>
              <th>GFS</th>
              <th>ICON</th>
              <th>Минимум</th>
              <th>Источник min</th>
              <th>Максимум</th>
              <th>Источник max</th>
              <th>Разброс</th>
              <th>Расхождение</th>
              <th>Пик</th>
              <th>Время пика</th>
              <th>Длительность</th>
              <th>Согласие</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((point) => {
              const stats = point.precipitation_analysis.daily_total;
              const maxSource = stats.maximum_source;
              return (
                <tr
                  key={point.point.id}
                  onClick={() => onSelect(point.point.id)}
                >
                  <td>
                    <button className="link-button">{point.point.name}</button>
                  </td>
                  <td>{number(stats.mean)} мм</td>
                  <td>{number(stats.median)} мм</td>
                  {["ECMWF IFS", "NOAA GFS", "DWD ICON"].map((model) => (
                    <td
                      key={model}
                      className={maxSource === model ? "model-maximum" : ""}
                    >
                      {value(point, model) == null
                        ? "Нет данных"
                        : `${number(value(point, model))} мм`}
                      {maxSource === model && " · максимум"}
                    </td>
                  ))}
                  <td>{number(stats.minimum)} мм</td>
                  <td>{stats.minimum_source ?? "Нет данных"}</td>
                  <td>{number(stats.maximum)} мм</td>
                  <td>{maxSource ?? "Нет данных"}</td>
                  <td>{number(stats.range)} мм</td>
                  <td>
                    {point.precipitation_analysis.relative_spread_pct == null
                      ? "—"
                      : `${number(point.precipitation_analysis.relative_spread_pct, 0)}%`}
                  </td>
                  <td>
                    {number(point.precipitation_analysis.peak_value)} мм/ч
                  </td>
                  <td>
                    {point.precipitation_analysis.peak_time
                      ? new Date(
                          point.precipitation_analysis.peak_time,
                        ).toLocaleTimeString("ru-RU", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      : "Нет данных"}
                  </td>
                  <td>{point.precipitation_analysis.duration_hours} ч</td>
                  <td>
                    <AgreementBadge
                      level={stats.agreement ?? "недостаточно данных"}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
