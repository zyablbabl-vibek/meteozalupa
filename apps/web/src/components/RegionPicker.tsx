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
  const districts = Object.entries(
    regions.reduce<Record<string, Region[]>>((groups, region) => {
      (groups[region.federal_district] ??= []).push(region);
      return groups;
    }, {}),
  ).sort(([left], [right]) => left.localeCompare(right, "ru"));

  return (
    <label className="region-picker">
      <span>Субъект РФ</span>
      <select
        aria-label="Регион России"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        {districts.map(([district, districtRegions]) => (
          <optgroup key={district} label={district}>
            {[...districtRegions]
              .sort((left, right) => left.name.localeCompare(right.name, "ru"))
              .map((region) => (
                <option key={region.id} value={region.id}>
                  {region.name}
                </option>
              ))}
          </optgroup>
        ))}
      </select>
    </label>
  );
}
