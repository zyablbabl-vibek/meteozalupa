import type { Region } from "../types/weather";
import { RegionPicker } from "./RegionPicker";

export function RegionHeader({
  regions,
  region,
  lastUpdated,
  dataMode,
  modelAvailability,
  refreshing,
  onRegionChange,
  onRefresh,
}: {
  regions: Region[];
  region: Region;
  lastUpdated?: string;
  dataMode?: "mock" | "live";
  modelAvailability?: Record<string, boolean>;
  refreshing: boolean;
  onRegionChange: (regionId: string) => void;
  onRefresh: () => void;
}) {
  return (
    <header>
      <div className="product-heading">
        <span className="eyebrow">Погода Дальнего Востока</span>
        <h1>Прогноз по {region.name_prepositional}</h1>
        <p>
          Основной часовой пояс: {region.primary_timezone}
          {lastUpdated
            ? ` · Обновлено ${new Date(lastUpdated).toLocaleString("ru-RU", {
                timeZone: region.primary_timezone,
              })}`
            : ""}
        </p>
      </div>
      <div className="header-actions">
        <RegionPicker
          regions={regions}
          value={region.id}
          onChange={onRegionChange}
        />
        <button onClick={onRefresh} disabled={refreshing}>
          {refreshing ? "Обновляем регион…" : "Обновить данные региона"}
        </button>
        {modelAvailability && (
          <div className="header-models" aria-label="Доступность моделей">
            {["ECMWF IFS", "NOAA GFS", "DWD ICON"].map((model) => (
              <span
                key={model}
                className={modelAvailability[model] ? "available" : "missing"}
              >
                {model}: {modelAvailability[model] ? "доступен" : "недоступен"}
              </span>
            ))}
          </div>
        )}
        {dataMode && (
          <span
            className={`mode ${dataMode}`}
            title={
              dataMode === "mock"
                ? "Детерминированные демонстрационные данные"
                : "Живой прогноз ECMWF, GFS и ICON через Open-Meteo"
            }
          >
            {dataMode === "mock" ? "Демо-данные" : "Live · Open-Meteo"}
          </span>
        )}
      </div>
    </header>
  );
}
