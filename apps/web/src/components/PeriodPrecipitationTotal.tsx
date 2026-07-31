import type { PeriodSummary } from "../types/weather";
import { number } from "../utils/format";

const MODEL_SHORT_NAMES: Record<string, string> = {
  "ECMWF IFS": "ECMWF",
  "NOAA GFS": "GFS",
  "DWD ICON": "ICON",
};

const dayWord = (count: number) => {
  const lastTwo = count % 100;
  const last = count % 10;
  if (lastTwo >= 11 && lastTwo <= 14) return "дней";
  if (last === 1) return "день";
  if (last >= 2 && last <= 4) return "дня";
  return "дней";
};

export function PeriodPrecipitationTotal({
  dayCount,
  regional,
  wettestPoint,
}: {
  dayCount: number;
  regional: PeriodSummary["regional_precipitation"];
  wettestPoint: PeriodSummary["precipitation"];
}) {
  const modelTotals = Object.entries(regional.models).filter(
    (entry): entry is [string, number] => entry[1] != null,
  );

  return (
    <div className="period-total">
      <span>
        Суммарные осадки за {dayCount} {dayWord(dayCount)}
      </span>
      <strong>{number(regional.statistics.mean)} мм</strong>
      <small>Среднее накопление по контрольным точкам региона</small>
      {modelTotals.length > 0 && (
        <small className="period-total-models">
          {modelTotals
            .map(
              ([model, value]) =>
                `${MODEL_SHORT_NAMES[model] ?? model} ${number(value)} мм`,
            )
            .join(" · ")}
        </small>
      )}
      <small className="period-total-maximum">
        Максимум в отдельной точке:{" "}
        <b>
          {number(wettestPoint.statistics.mean)} мм · {wettestPoint.point.name}
        </b>
      </small>
    </div>
  );
}
