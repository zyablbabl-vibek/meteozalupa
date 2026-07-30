import type { PointSummary } from "../types/weather";
import { number, temperature } from "../utils/format";
import { AgreementBadge } from "./AgreementBadge";

const model = (item: PointSummary, name: string) => item.models[name];

export function PointsTable({
  points,
  onSelect,
}: {
  points: PointSummary[];
  onSelect: (id: string) => void;
}) {
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Населённый пункт</th>
            <th>Средняя</th>
            <th>ECMWF</th>
            <th>GFS</th>
            <th>ICON</th>
            <th>Мин.</th>
            <th>Макс.</th>
            <th>Разброс</th>
            <th>Согласие</th>
            <th>Осадки</th>
            <th>Порыв</th>
          </tr>
        </thead>
        <tbody>
          {points.map((item) => (
            <tr key={item.point.id} onClick={() => onSelect(item.point.id)}>
              <td>
                <button className="link-button">{item.point.name}</button>
                {item.incomplete && <small> неполно</small>}
              </td>
              <td>{temperature(item.mean_temperature)}</td>
              <td>{temperature(model(item, "ECMWF IFS"))}</td>
              <td>{temperature(model(item, "NOAA GFS"))}</td>
              <td>{temperature(model(item, "DWD ICON"))}</td>
              <td>{temperature(item.minimum)}</td>
              <td>{temperature(item.maximum)}</td>
              <td>{number(item.spread)}°</td>
              <td>
                <AgreementBadge level={item.agreement} />
              </td>
              <td>{number(item.precipitation.mean)} мм</td>
              <td>{number(item.max_gust)} м/с</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
