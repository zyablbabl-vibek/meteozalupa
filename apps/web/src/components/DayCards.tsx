import type { DailySummary } from "../types/weather";
import { AgreementBadge } from "./AgreementBadge";
import { number, temperature } from "../utils/format";

const formatter = new Intl.DateTimeFormat("ru-RU", {
  weekday: "short",
  day: "numeric",
  month: "short",
  timeZone: "Asia/Yakutsk",
});

export function DayCards({
  days,
  selected,
  onSelect,
}: {
  days: DailySummary[];
  selected: string;
  onSelect: (date: string) => void;
}) {
  return (
    <div className="day-strip">
      {days.map((day, index) => (
        <button
          key={day.date}
          className={`day-card ${selected === day.date ? "active" : ""}`}
          onClick={() => onSelect(day.date)}
        >
          <span>
            {index === 0
              ? "Сегодня"
              : formatter.format(new Date(`${day.date}T03:00:00+09:00`))}
          </span>
          <strong>
            {temperature(day.minimum_temperature)}…{" "}
            {temperature(day.maximum_temperature)}
          </strong>
          <small>
            {number(day.precipitation_sum)} мм · {number(day.max_gust)} м/с
          </small>
          <AgreementBadge level={day.agreement} />
        </button>
      ))}
    </div>
  );
}
