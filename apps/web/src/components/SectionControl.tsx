import type { Section } from "../types/weather";

const OPTIONS: Array<[Section, string]> = [
  ["temperature", "Температура"],
  ["precipitation", "Осадки"],
  ["wind", "Ветер"],
];

export function SectionControl({
  value,
  onChange,
}: {
  value: Section;
  onChange: (value: Section) => void;
}) {
  return (
    <div className="section-tabs" aria-label="Погодный показатель">
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
