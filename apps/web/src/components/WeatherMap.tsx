import { CircleMarker, MapContainer, TileLayer, Tooltip } from "react-leaflet";
import type { PointSummary } from "../types/weather";
import { temperature } from "../utils/format";

const color = (value: number) =>
  value < 5
    ? "#3976a8"
    : value < 15
      ? "#2b8a7e"
      : value < 23
        ? "#d59632"
        : "#bd4b3e";

export function WeatherMap({
  points,
  onSelect,
}: {
  points: PointSummary[];
  onSelect: (id: string) => void;
}) {
  return (
    <div className="map-wrap">
      <MapContainer center={[52.2, 127.5]} zoom={5} scrollWheelZoom={false}>
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {points.map((item) => (
          <CircleMarker
            key={item.point.id}
            center={[item.point.latitude, item.point.longitude]}
            radius={7 + Math.min(item.spread, 10)}
            pathOptions={{
              color: "#fff",
              weight: 2,
              fillColor: color(item.mean_temperature),
              fillOpacity: 0.92,
            }}
            eventHandlers={{ click: () => onSelect(item.point.id) }}
          >
            <Tooltip>
              <b>{item.point.name}</b>
              <br />
              Средняя: {temperature(item.mean_temperature)}
              <br />
              Разброс: {item.spread.toFixed(1)} °C
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
      <p className="caption">
        Прогноз рассчитан по контрольным точкам, а не по непрерывной сетке всей
        области.
      </p>
    </div>
  );
}
