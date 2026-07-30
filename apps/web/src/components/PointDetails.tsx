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
  BarChart,
  Bar,
} from "recharts";
import type { PointForecast } from "../types/weather";
import { number } from "../utils/format";

export function PointDetails({
  data,
  dimPastHours = false,
}: {
  data: PointForecast;
  dimPastHours?: boolean;
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
    value: row.statistics.mean,
  }));
  const wind = data.series.wind_speed_10m.map((row, i) => ({
    time: new Date(row.forecast_time_local).getHours(),
    speed: row.statistics.mean,
    gust: data.series.wind_gusts_10m[i]?.statistics.mean,
  }));
  return (
    <section className="details">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Подробный прогноз</span>
          <h2>{data.point.name}</h2>
        </div>
      </div>
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
      <div className="chart-grid">
        <div>
          <h3>Осадки</h3>
          <div className="small-chart">
            <ResponsiveContainer>
              <BarChart data={rain}>
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" name="мм" fill="#4e8aa0" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div>
          <h3>Ветер и порывы</h3>
          <div className="small-chart">
            <ResponsiveContainer>
              <ComposedChart data={wind}>
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line dataKey="speed" name="Скорость" stroke="#397c73" />
                <Line dataKey="gust" name="Порывы" stroke="#b65b3a" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
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
    </section>
  );
}
