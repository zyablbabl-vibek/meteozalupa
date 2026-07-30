import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Bar,
} from "recharts";
import type { PointForecast, Section } from "../types/weather";
import { number } from "../utils/format";

export function PointDetails({
  data,
  dimPastHours = false,
  section = "temperature",
}: {
  data: PointForecast;
  dimPastHours?: boolean;
  section?: Section;
}) {
  const temps = data.series.temperature_2m.map((row) => ({
    time: new Date(row.forecast_time_local).toLocaleTimeString("ru-RU", {
      hour: "2-digit",
      minute: "2-digit",
    }),
    ECMWF: row.models["ECMWF IFS"],
    GFS: row.models["NOAA GFS"],
    ICON: row.models["DWD ICON"],
    mean: row.statistics.mean,
    min: row.statistics.minimum,
    range: (row.statistics.maximum ?? 0) - (row.statistics.minimum ?? 0),
    isPast: dimPastHours && new Date(row.forecast_time_local) < new Date(),
  }));
  const rain = data.series.precipitation.map((row) => ({
    time: new Date(row.forecast_time_local).getHours(),
    ECMWF: row.models["ECMWF IFS"],
    GFS: row.models["NOAA GFS"],
    ICON: row.models["DWD ICON"],
    mean: row.statistics.mean,
    spread: row.statistics.range,
  }));
  const wind = data.series.wind_speed_10m.map((row, i) => ({
    time: new Date(row.forecast_time_local).getHours(),
    speed: row.statistics.mean,
    gust: data.series.wind_gusts_10m[i]?.statistics.mean,
    ECMWF: row.models["ECMWF IFS"],
    GFS: row.models["NOAA GFS"],
    ICON: row.models["DWD ICON"],
  }));
  const gusts = data.series.wind_gusts_10m.map((row) => ({
    time: new Date(row.forecast_time_local).getHours(),
    ECMWF: row.models["ECMWF IFS"],
    GFS: row.models["NOAA GFS"],
    ICON: row.models["DWD ICON"],
    mean: row.statistics.mean,
    min: row.statistics.minimum,
    range: (row.statistics.maximum ?? 0) - (row.statistics.minimum ?? 0),
  }));
  const directions = data.series.wind_direction_10m.map((row) => ({
    time: new Date(row.forecast_time_local).getHours(),
    ECMWF: row.models["ECMWF IFS"],
    GFS: row.models["NOAA GFS"],
    ICON: row.models["DWD ICON"],
    mean: row.statistics.mean,
  }));
  return (
    <section className="details">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Подробный прогноз</span>
          <h2>{data.point.name}</h2>
        </div>
      </div>
      {section === "temperature" && (
        <>
          <h3>Температура по часам</h3>
          <div className="chart">
            <ResponsiveContainer>
              <ComposedChart data={temps}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis unit="°" />
                <Tooltip />
                <Legend />
                <Area
                  dataKey="min"
                  stackId="band"
                  stroke="none"
                  fill="transparent"
                />
                <Area
                  dataKey="range"
                  stackId="band"
                  stroke="none"
                  fill="#b8d7d4"
                  fillOpacity={0.45}
                />
                <Line dataKey="ECMWF" stroke="#326789" dot={false} />
                <Line dataKey="GFS" stroke="#c87a34" dot={false} />
                <Line dataKey="ICON" stroke="#71864b" dot={false} />
                <Line
                  dataKey="mean"
                  name="Среднее"
                  stroke="#152f38"
                  strokeWidth={3}
                  dot={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
      {section === "precipitation" && (
        <div>
          <h3>Почасовые осадки по моделям</h3>
          <div className="chart">
            <ResponsiveContainer>
              <ComposedChart data={rain}>
                <XAxis dataKey="time" />
                <YAxis unit=" мм/ч" />
                <Tooltip />
                <Legend />
                <Bar dataKey="ECMWF" fill="#326789" />
                <Bar dataKey="GFS" fill="#c87a34" />
                <Bar dataKey="ICON" fill="#71864b" />
                <Line dataKey="mean" name="Среднее" stroke="#173b45" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
      {section === "wind" && (
        <div className="chart-grid">
          <div>
            <h3>Средняя скорость ветра</h3>
            <div className="small-chart">
              <ResponsiveContainer>
                <ComposedChart data={wind}>
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line dataKey="ECMWF" stroke="#326789" />
                  <Line dataKey="GFS" stroke="#c87a34" />
                  <Line dataKey="ICON" stroke="#71864b" />
                  <Line
                    dataKey="speed"
                    name="Среднее"
                    stroke="#173b45"
                    strokeWidth={3}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div>
            <h3>Порывы ветра</h3>
            <div className="small-chart">
              <ResponsiveContainer>
                <ComposedChart data={gusts}>
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Area
                    dataKey="min"
                    stackId="gust-band"
                    stroke="none"
                    fill="transparent"
                  />
                  <Area
                    dataKey="range"
                    stackId="gust-band"
                    stroke="none"
                    fill="#f0c7bb"
                    fillOpacity={0.4}
                  />
                  <Line dataKey="ECMWF" stroke="#326789" />
                  <Line dataKey="GFS" stroke="#c87a34" />
                  <Line dataKey="ICON" stroke="#71864b" />
                  <Line
                    dataKey="mean"
                    name="Среднее"
                    stroke="#173b45"
                    strokeWidth={3}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="direction-strip">
            <h3>Направление по времени</h3>
            <div>
              {directions.map((row) => (
                <span
                  key={row.time}
                  title={`ECMWF ${number(row.ECMWF, 0)}°, GFS ${number(row.GFS, 0)}°, ICON ${number(row.ICON, 0)}°`}
                >
                  <small>{row.time}:00</small>
                  <b style={{ transform: `rotate(${row.mean ?? 0}deg)` }}>↑</b>
                  <em>{number(row.mean, 0)}°</em>
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
      {section === "temperature" && (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Время</th>
                <th>ECMWF</th>
                <th>GFS</th>
                <th>ICON</th>
                <th>Среднее</th>
                <th>Мин.</th>
                <th>Макс.</th>
              </tr>
            </thead>
            <tbody>
              {temps.map((row) => (
                <tr key={row.time} className={row.isPast ? "past-hour" : ""}>
                  <td>{row.time}</td>
                  <td>{number(row.ECMWF)}°</td>
                  <td>{number(row.GFS)}°</td>
                  <td>{number(row.ICON)}°</td>
                  <td>{number(row.mean)}°</td>
                  <td>{number(row.min)}°</td>
                  <td>{number((row.min ?? 0) + row.range)}°</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
