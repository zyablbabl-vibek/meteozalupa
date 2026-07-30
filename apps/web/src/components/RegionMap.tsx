import type { GeoJsonObject } from "geojson";
import {
  CircleMarker,
  GeoJSON,
  MapContainer,
  TileLayer,
  Tooltip,
} from "react-leaflet";
import type { PointSummary, Region, Section } from "../types/weather";
import { number, temperature } from "../utils/format";

const color = (value: number) =>
  value < 5
    ? "#3976a8"
    : value < 15
      ? "#2b8a7e"
      : value < 23
        ? "#d59632"
        : "#bd4b3e";

export function RegionMap({
  region,
  geojson,
  points,
  onSelect,
  section = "temperature",
}: {
  region: Region;
  geojson?: GeoJsonObject;
  points: PointSummary[];
  onSelect: (id: string) => void;
  section?: Section;
}) {
  const markerValue = (item: PointSummary): number | null =>
    section === "precipitation"
      ? (item.precipitation.mean ?? null)
      : section === "wind"
        ? (item.wind_speed.mean ?? null)
        : item.mean_temperature;
  const markerColor = (item: PointSummary) => {
    const value = markerValue(item);
    if (value == null) return "#9da8a7";
    if (section === "precipitation")
      return value < 1
        ? "#a9c6cf"
        : value < 5
          ? "#4e8aa0"
          : value < 15
            ? "#3566a0"
            : "#203b7b";
    if (section === "wind")
      return value < 4
        ? "#6aa89d"
        : value < 8
          ? "#d3a544"
          : value < 12
            ? "#c46d39"
            : "#a23835";
    return color(value);
  };
  const radius = (item: PointSummary) => {
    if (section === "wind") {
      return item.max_gust == null ? 7 : 7 + Math.min(item.max_gust, 15) / 2;
    }
    if (section === "precipitation") {
      return item.precipitation.range == null
        ? 7
        : 7 + Math.min(item.precipitation.range, 10);
    }
    return 7 + Math.min(item.spread, 10);
  };
  return (
    <div className="map-wrap">
      <MapContainer
        key={region.id}
        center={[region.map_center_latitude, region.map_center_longitude]}
        zoom={region.map_zoom}
        scrollWheelZoom={false}
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {geojson && (
          <GeoJSON
            data={geojson}
            style={{
              color: "#2c6e73",
              weight: 2,
              fillColor: "#78a99f",
              fillOpacity: 0.08,
            }}
          />
        )}
        {points.map((item) => (
          <CircleMarker
            key={item.point.id}
            center={[item.point.latitude, item.point.longitude]}
            radius={radius(item)}
            pathOptions={{
              color: "#fff",
              weight: 2,
              fillColor: markerColor(item),
              fillOpacity: 0.92,
            }}
            eventHandlers={{ click: () => onSelect(item.point.id) }}
          >
            <Tooltip>
              <b>{item.point.name}</b>
              <br />
              Местное время: {item.point.timezone}
              <br />
              {section === "temperature" && (
                <>
                  Средняя: {temperature(item.mean_temperature)}
                  <br />
                  Разброс: {item.spread.toFixed(1)} °C
                </>
              )}
              {section === "precipitation" && (
                <>
                  ECMWF:{" "}
                  {number(
                    item.precipitation_analysis.daily_total.model_values[
                      "ECMWF IFS"
                    ],
                  )}{" "}
                  мм
                  <br />
                  GFS:{" "}
                  {number(
                    item.precipitation_analysis.daily_total.model_values[
                      "NOAA GFS"
                    ],
                  )}{" "}
                  мм
                  <br />
                  ICON:{" "}
                  {number(
                    item.precipitation_analysis.daily_total.model_values[
                      "DWD ICON"
                    ],
                  )}{" "}
                  мм
                  <br />
                  Среднее: {number(item.precipitation.mean)} мм
                  <br />
                  Пик: {number(item.precipitation_analysis.peak_value)} мм/ч
                </>
              )}
              {section === "wind" && (
                <>
                  Средняя скорость: {number(item.wind_speed.mean)} м/с
                  <br />
                  Максимальный порыв:{" "}
                  {number(item.wind_analysis.maximum_gust.maximum)} м/с
                  <br />
                  Источник: {item.wind_analysis.maximum_gust.maximum_source}
                  <br />
                  Направление:{" "}
                  {item.wind_analysis.direction_label ?? "расходится"}
                </>
              )}
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
      <p className="caption">
        Карта показывает прогноз в контрольных точках. Значения между точками не
        рассчитываются.
      </p>
    </div>
  );
}
