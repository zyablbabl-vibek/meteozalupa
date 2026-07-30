import { useMemo, useState } from "react";
import type { PointSummary } from "../types/weather";
import { number } from "../utils/format";
import { AgreementBadge } from "./AgreementBadge";

type Sort = "gust" | "speed" | "spread";

export function WindTable({
  points,
  onSelect,
}: {
  points: PointSummary[];
  onSelect: (id: string) => void;
}) {
  const [sort, setSort] = useState<Sort>("gust");
  const [attentionOnly, setAttentionOnly] = useState(false);
  const rows = useMemo(
    () =>
      points
        .filter(
          (point) =>
            !attentionOnly ||
            (point.wind_analysis.maximum_gust.maximum != null &&
              point.wind_analysis.maximum_gust.maximum >= 15) ||
            (point.wind_analysis.maximum_direction_disagreement_deg != null &&
              point.wind_analysis.maximum_direction_disagreement_deg >= 90),
        )
        .sort((a, b) => {
          const metric =
            sort === "gust"
              ? "maximum_gust"
              : sort === "speed"
                ? "mean_speed"
                : "maximum_speed";
          const aStats = a.wind_analysis[metric];
          const bStats = b.wind_analysis[metric];
          return sort === "spread"
            ? (bStats.range ?? -1) - (aStats.range ?? -1)
            : (bStats.maximum ?? bStats.mean ?? -1) -
                (aStats.maximum ?? aStats.mean ?? -1);
        }),
    [points, attentionOnly, sort],
  );
  return (
    <>
      <div className="table-tools">
        <label>
          Сортировка{" "}
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as Sort)}
          >
            <option value="gust">По максимальному порыву</option>
            <option value="speed">По средней скорости</option>
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
              <th>Средняя скорость</th>
              <th>ECMWF скорость</th>
              <th>GFS скорость</th>
              <th>ICON скорость</th>
              <th>Макс. порыв</th>
              <th>ECMWF порыв</th>
              <th>GFS порыв</th>
              <th>ICON порыв</th>
              <th>Источник max</th>
              <th>Разброс</th>
              <th>Направление</th>
              <th>ECMWF</th>
              <th>GFS</th>
              <th>ICON</th>
              <th>Угловой разброс</th>
              <th>Согласие</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((point) => {
              const wind = point.wind_analysis;
              const speed = wind.mean_speed;
              const gust = wind.maximum_gust;
              return (
                <tr
                  key={point.point.id}
                  className={
                    wind.maximum_direction_disagreement_deg != null &&
                    wind.maximum_direction_disagreement_deg >= 90
                      ? "direction-disagreement"
                      : ""
                  }
                  onClick={() => onSelect(point.point.id)}
                >
                  <td>
                    <button className="link-button">{point.point.name}</button>
                  </td>
                  <td>{number(speed.mean)} м/с</td>
                  {["ECMWF IFS", "NOAA GFS", "DWD ICON"].map((model) => (
                    <td key={`s-${model}`}>
                      {speed.model_values[model] == null
                        ? "Нет данных"
                        : `${number(speed.model_values[model])} м/с`}
                    </td>
                  ))}
                  <td>{number(gust.maximum)} м/с</td>
                  {["ECMWF IFS", "NOAA GFS", "DWD ICON"].map((model) => (
                    <td
                      key={`g-${model}`}
                      className={
                        gust.maximum_source === model ? "model-maximum" : ""
                      }
                    >
                      {gust.model_values[model] == null
                        ? "Нет данных"
                        : `${number(gust.model_values[model])} м/с${gust.maximum_source === model ? " · максимум" : ""}`}
                    </td>
                  ))}
                  <td>{gust.maximum_source ?? "Нет данных"}</td>
                  <td>{number(gust.range)} м/с</td>
                  <td>
                    {wind.circular_mean_direction_deg == null
                      ? "Направления расходятся"
                      : `${number(wind.circular_mean_direction_deg, 0)}° — ${wind.direction_label} ↑`}
                  </td>
                  {["ECMWF IFS", "NOAA GFS", "DWD ICON"].map((model) => (
                    <td key={`d-${model}`}>
                      {wind.directions_by_model[model] == null
                        ? "Нет данных"
                        : `${number(wind.directions_by_model[model], 0)}° ${wind.direction_labels_by_model[model]}`}
                    </td>
                  ))}
                  <td>{number(wind.maximum_direction_disagreement_deg, 0)}°</td>
                  <td>
                    <AgreementBadge
                      level={gust.agreement ?? wind.direction_agreement}
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
