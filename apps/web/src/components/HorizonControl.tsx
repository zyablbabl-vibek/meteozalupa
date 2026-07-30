import type { Horizon } from "../types/weather";

const OPTIONS: Array<[Horizon, string]> = [
  ["today", "Сегодня"],
  ["3d", "3 дня"],
  ["7d", "7 дней"],
];

export function HorizonControl({
  value,
  onChange,
}: {
  value: Horizon;
  onChange: (value: Horizon) => void;
}) {
  return (
    <div className="segmented" aria-label="Период прогноза">
      {OPTIONS.map(([id, label]) => (
        <button
          key={id}
          className={value === id ? "active" : ""}
          aria-pressed={value === id}
          onClick={() => onChange(id)}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
