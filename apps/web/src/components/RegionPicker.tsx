import type { Region } from "../types/weather";

export function RegionPicker({
  regions,
  value,
  onChange,
}: {
  regions: Region[];
  value: string;
  onChange: (regionId: string) => void;
}) {
  return (
    <label className="region-picker">
      <span>Регион</span>
      <select
        aria-label="Регион Дальнего Востока"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {regions.map((region) => (
          <option key={region.id} value={region.id}>
            {region.name}
          </option>
        ))}
      </select>
    </label>
  );
}
